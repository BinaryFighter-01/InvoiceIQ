"""
OpenRouter API Client for Qwen3.7-Plus
"""

import os
import json
import base64
import requests
from io import BytesIO
from PIL import Image
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class OpenRouterClient:
    """Client for OpenRouter API with Qwen model."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or os.getenv('MODEL_NAME', 'qwen/qwen-2-vl-7b-instruct')
        self.base_url = 'https://openrouter.ai/api/v1/chat/completions'
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    
    @staticmethod
    def repair_json(json_str: str) -> str:
        """
        Attempt to repair common JSON syntax errors.
        
        Common issues:
        - Missing closing brackets/braces
        - Trailing commas
        - Truncated responses
        - Unquoted property names
        - Single quotes instead of double quotes
        """
        import re
        
        # Remove trailing commas before closing brackets
        json_str = json_str.replace(',]', ']').replace(',}', '}')
        
        # Replace single quotes with double quotes (but not inside strings)
        # This is a simple heuristic - may not work for all cases
        json_str = json_str.replace("'", '"')
        
        # Fix common unquoted property names (e.g., {description: "value"} -> {"description": "value"})
        # Match word characters followed by colon
        json_str = re.sub(r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        # Remove any non-JSON content before first {
        first_brace = json_str.find('{')
        if first_brace > 0:
            json_str = json_str[first_brace:]
            print(f"🔧 Removed {first_brace} characters before first brace")
        
        # Remove any non-JSON content after last }
        last_brace = json_str.rfind('}')
        if last_brace >= 0 and last_brace < len(json_str) - 1:
            extra_chars = len(json_str) - last_brace - 1
            json_str = json_str[:last_brace + 1]
            print(f"🔧 Removed {extra_chars} characters after last brace")
        
        # Count opening and closing brackets
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        # Add missing closing brackets
        if open_brackets > close_brackets:
            json_str += ']' * (open_brackets - close_brackets)
            print(f"🔧 Added {open_brackets - close_brackets} closing bracket(s)")
        
        if open_braces > close_braces:
            json_str += '}' * (open_braces - close_braces)
            print(f"🔧 Added {open_braces - close_braces} closing brace(s)")
        
        return json_str
    
    @staticmethod
    def image_to_base64(pil_image: Image.Image, format: str = 'PNG', max_size: int = 2048) -> str:
        """
        Convert PIL Image to base64 string with size optimization.
        
        Args:
            pil_image: PIL Image object
            format: Image format (PNG or JPEG)
            max_size: Maximum dimension (width or height)
        """
        # Resize if image is too large
        width, height = pil_image.size
        if width > max_size or height > max_size:
            # Calculate new size maintaining aspect ratio
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"🔄 Image resized from {width}x{height} to {new_width}x{new_height}")
        
        # Convert to base64
        buffered = BytesIO()
        
        # Use JPEG for larger images to reduce size
        if width * height > 1000000:  # If > 1MP, use JPEG
            format = 'JPEG'
            pil_image = pil_image.convert('RGB')  # JPEG doesn't support transparency
        
        pil_image.save(buffered, format=format, quality=85 if format == 'JPEG' else None)
        img_bytes = buffered.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # Log size
        size_mb = len(img_bytes) / (1024 * 1024)
        print(f"📦 Image encoded: {size_mb:.2f}MB as {format}")
        
        return f"data:image/{format.lower()};base64,{img_base64}"
    
    def extract_invoice(
        self,
        image: Image.Image,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2500
    ) -> tuple[dict, dict]:
        """
        Extract invoice data using vision model.
        
        Returns:
            Tuple of (extracted_data_dict, raw_response_dict)
        """
        # Convert image to base64
        image_b64 = self.image_to_base64(image)
        
        # Prepare request
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': user_prompt
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': image_b64
                            }
                        }
                    ]
                }
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
            # Disable chain-of-thought thinking for Qwen3 and similar models.
            # These passes are pure OCR copy tasks — reasoning wastes tokens and
            # causes "No JSON found" errors when the budget runs out mid-think.
            'thinking': {'type': 'disabled'},
        }
        
        # Make request with retry logic
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                timeout_duration = 300  # 5 minutes timeout for complex invoices
                print(f"🌐 Sending request to {self.model}... (attempt {retry_count + 1}/{max_retries + 1}, timeout: {timeout_duration}s)")
                
                response = requests.post(
                    self.base_url, 
                    headers=headers, 
                    json=payload, 
                    timeout=timeout_duration
                )
                
                # Handle HTTP errors with detailed error info
                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', {})
                        if isinstance(error_msg, dict):
                            error_msg = error_msg.get('message', str(error_msg))
                        api_error = f"API Error ({response.status_code}): {error_msg}"
                    except:
                        api_error = f"API Error ({response.status_code}): {response.text}"
                    
                    print(f"❌ {api_error}")
                    return {'error': api_error}, {}
                
                # Try to parse JSON response
                try:
                    response_data = response.json()
                except json.JSONDecodeError as json_err:
                    # Response is not valid JSON
                    error_msg = f"API returned invalid JSON: {str(json_err)}"
                    print(f"❌ {error_msg}")
                    print(f"📄 Response text (first 500 chars): {response.text[:500]}")
                    return {'error': error_msg, 'raw_response': response.text[:1000]}, {}
                
                break  # Success, exit retry loop
                
            except requests.exceptions.Timeout:
                retry_count += 1
                if retry_count > max_retries:
                    error_msg = f"Request timeout after {max_retries + 1} attempts ({timeout_duration}s each). The invoice may be too complex or the server is slow."
                    print(f"❌ {error_msg}")
                    return {'error': error_msg}, {}
                else:
                    print(f"⚠️  Timeout on attempt {retry_count}, retrying...")
                    continue
                    
            except requests.exceptions.HTTPError as e:
                # Handle specific HTTP errors
                status_code = e.response.status_code
                if status_code == 402:
                    error_msg = "❌ Payment Required: Your OpenRouter account has insufficient credits. Please add funds at https://openrouter.ai/account/billing/overview"
                elif status_code == 401:
                    error_msg = "❌ Unauthorized: Invalid or expired API key. Please check your OPENROUTER_API_KEY in .env"
                elif status_code == 429:
                    error_msg = "❌ Rate Limited: Too many requests. Please wait a moment and try again."
                else:
                    try:
                        error_data = e.response.json()
                        error_msg = f"API Error ({status_code}): {error_data.get('error', {}).get('message', str(error_data))}"
                    except:
                        error_msg = f"API Error ({status_code}): {e.response.text}"
                
                print(error_msg)
                return {'error': error_msg}, {}
            except requests.exceptions.RequestException as e:
                error_msg = f"API request failed: {str(e)}"
                print(f"❌ {error_msg}")
                return {'error': error_msg}, {}
            except Exception as e:
                error_msg = f"Unexpected error during request: {str(e)}"
                print(f"❌ {error_msg}")
                return {'error': error_msg}, {}
        
        # Process response
        try:
            
            print(f"✅ API response received")
            print(f"📊 Response keys: {list(response_data.keys())}")
            
            # Debug: Print response structure
            if 'choices' in response_data:
                print(f"📝 Choices length: {len(response_data.get('choices', []))}")
                if len(response_data['choices']) > 0:
                    print(f"📝 First choice keys: {list(response_data['choices'][0].keys())}")
            else:
                print(f"⚠️  No 'choices' in response. Response: {response_data}")
            
            # Extract text response
            if 'choices' in response_data and len(response_data['choices']) > 0:
                message = response_data['choices'][0].get('message', {})
                text_response = message.get('content', '')
                
                if not text_response:
                    print(f"⚠️  Empty content in message: {message}")
                    return {'error': 'Model returned empty response'}, response_data
                
                print(f"📄 Response length: {len(text_response)} characters")
                
                # Parse JSON from response
                try:
                    # Clean response - remove markdown fences if present
                    text_response = text_response.strip()
                    
                    # Strip <think>...</think> blocks emitted by Qwen3 and similar
                    # reasoning models before the actual JSON output
                    import re as _re
                    text_response = _re.sub(r'<think>.*?</think>', '', text_response, flags=_re.DOTALL).strip()
                    
                    # Remove markdown code fences (```json ... ``` or ``` ... ```)
                    if text_response.startswith('```'):
                        # Find the end of the code block
                        end_fence = text_response.rfind('```')
                        if end_fence > 0:
                            text_response = text_response[text_response.find('\n')+1:end_fence]
                        else:
                            # Malformed, try to extract anyway
                            text_response = text_response[3:]
                    
                    text_response = text_response.strip()
                    
                    # Find JSON content
                    start_idx = text_response.find('{')
                    end_idx = text_response.rfind('}') + 1
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = text_response[start_idx:end_idx]
                        print(f"📝 JSON string length: {len(json_str)}")
                        
                        # Try to parse
                        try:
                            extracted_data = json.loads(json_str)
                            print(f"✅ JSON parsed successfully")
                            return extracted_data, response_data
                        except json.JSONDecodeError as parse_err:
                            print(f"❌ JSON decode failed at position {parse_err.pos}: {parse_err.msg}")
                            
                            # Show context around error
                            start_context = max(0, parse_err.pos - 100)
                            end_context = min(len(json_str), parse_err.pos + 100)
                            error_context = json_str[start_context:end_context]
                            
                            # Highlight error position
                            error_offset = parse_err.pos - start_context
                            context_with_marker = (
                                error_context[:error_offset] + 
                                ' <<<ERROR>>> ' + 
                                error_context[error_offset:]
                            )
                            
                            print(f"Error context:\n{context_with_marker}")
                            
                            # Try to repair JSON
                            print("🔧 Attempting to repair JSON...")
                            repaired_json = self.repair_json(json_str)
                            
                            try:
                                extracted_data = json.loads(repaired_json)
                                print(f"✅ JSON repaired and parsed successfully!")
                                return extracted_data, response_data
                            except json.JSONDecodeError as repair_err:
                                print(f"❌ Repair failed: {repair_err.msg}")
                                
                                # Save the failed JSON for debugging
                                print(f"\n🔍 FAILED JSON (first 1000 chars):")
                                print(json_str[:1000])
                                print(f"\n🔍 FAILED JSON (last 500 chars):")
                                print(json_str[-500:])
                                
                                # Provide helpful suggestion
                                if "Expecting property name enclosed in double quotes" in str(parse_err):
                                    print("💡 Error: Model used unquoted property names or single quotes")
                                    print("   The model must use double quotes for all property names")
                                elif "Expecting ',' delimiter" in str(parse_err):
                                    print("💡 Hint: Model likely generated invalid JSON syntax. Common causes:")
                                    print("   - Missing comma between object properties")
                                    print("   - Trailing comma before closing brace")
                                    print("   - Unquoted string values")
                                    print("   - Incomplete JSON (truncated response)")
                                elif "Expecting value" in str(parse_err):
                                    print("💡 Error: Missing value after colon or comma")
                                
                                raise parse_err  # Raise original error
                    else:
                        print(f"⚠️  No JSON found in response")
                        print(f"Full response: {text_response[:1000]}")
                        raise ValueError("No JSON object found in response")
                
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"❌ Parse error: {str(e)}")
                    # Return first 2000 chars for debugging
                    return {
                        'error': f'Failed to parse JSON response: {str(e)}',
                        'raw_response': text_response[:2000]
                    }, response_data
            
            print(f"❌ No valid response structure")
            return {'error': 'No response from model', 'debug': str(response_data)[:500]}, response_data
        
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing error in response processing: {e}")
            return {'error': 'Failed to parse model response'}, {}
        except Exception as e:
            error_msg = f"Unexpected error processing response: {str(e)}"
            print(f"❌ {error_msg}")
            return {'error': error_msg}, {}
    
    def get_reasoning_stream(self) -> str:
        """
        Generate a mock reasoning stream for the UI.
        In a real implementation, this could tap into model's chain-of-thought.
        """
        return "Processing invoice image...\n"
    
    def extract_invoice_two_pass(
        self,
        image: Image.Image,
        temperature: float = 0.1
    ) -> tuple[dict, dict]:
        """
        Extract invoice data using two-pass strategy for better accuracy.
        
        Pass 1a: Extract header fields only (500 tokens)
        Pass 1b: Extract totals fields only (300 tokens)
        Pass 2: Extract line items only (1500 tokens)
        
        Returns:
            Tuple of (merged_data_dict, metadata_dict)
        """
        from schema import get_header_prompt, get_totals_prompt, get_items_prompt
        
        print("\n" + "="*80)
        print("🔄 TWO-PASS EXTRACTION MODE")
        print("="*80)
        
        merged_data = {}
        pass_metadata = {}
        
        # Pass 1a: Header fields
        print("\n📋 Pass 1a: Extracting header fields...")
        header_system, header_user = get_header_prompt()
        
        header_data, header_response = self.extract_invoice(
            image,
            header_system,
            header_user,
            temperature=temperature,
            max_tokens=1000
        )
        
        if 'error' in header_data:
            return {
                'error': f"Pass 1a (Header) failed: {header_data['error']}",
                'failed_pass': 'header',
                'partial_results': {}
            }, {'pass_1a': header_response}
        
        merged_data.update(header_data)
        pass_metadata['pass_1a'] = {
            'fields_extracted': len(header_data),
            'response': header_response
        }
        print(f"✅ Pass 1a complete: {len(header_data)} header fields extracted")
        
        # Pass 1b: Totals fields
        print("\n💰 Pass 1b: Extracting totals fields...")
        totals_system, totals_user = get_totals_prompt()
        
        totals_data, totals_response = self.extract_invoice(
            image,
            totals_system,
            totals_user,
            temperature=temperature,
            max_tokens=1000
        )
        
        if 'error' in totals_data:
            return {
                'error': f"Pass 1b (Totals) failed: {totals_data['error']}",
                'failed_pass': 'totals',
                'partial_results': merged_data.copy()
            }, {'pass_1a': header_response, 'pass_1b': totals_response}
        
        merged_data.update(totals_data)
        pass_metadata['pass_1b'] = {
            'fields_extracted': len(totals_data),
            'response': totals_response
        }
        print(f"✅ Pass 1b complete: {len(totals_data)} totals fields extracted")
        
        # Pass 2: Line items
        print("\n📦 Pass 2: Extracting line items...")
        items_system, items_user = get_items_prompt()
        
        items_data, items_response = self.extract_invoice(
            image,
            items_system,
            items_user,
            temperature=temperature,
            max_tokens=3000  # Increased from 1500 to handle invoices with many items
        )
        
        if 'error' in items_data:
            return {
                'error': f"Pass 2 (Items) failed: {items_data['error']}",
                'failed_pass': 'items',
                'partial_results': merged_data.copy()
            }, {'pass_1a': header_response, 'pass_1b': totals_response, 'pass_2': items_response}
        
        # Merge items array
        merged_data['items'] = items_data.get('items', [])
        pass_metadata['pass_2'] = {
            'items_extracted': len(merged_data['items']),
            'response': items_response
        }
        print(f"✅ Pass 2 complete: {len(merged_data['items'])} items extracted")
        
        print("\n" + "="*80)
        print(f"✅ TWO-PASS EXTRACTION COMPLETE")
        print(f"   Header fields: {pass_metadata['pass_1a']['fields_extracted']}")
        print(f"   Totals fields: {pass_metadata['pass_1b']['fields_extracted']}")
        print(f"   Line items: {pass_metadata['pass_2']['items_extracted']}")
        print("="*80 + "\n")
        
        return merged_data, pass_metadata

    def extract_invoice_multipage(
        self,
        images: list[Image.Image],
        use_two_pass: bool = True,
        temperature: float = 0.1
    ) -> tuple[dict, dict]:
        """
        Extract invoice data from multi-page PDF.
        
        ⚠️ CRITICAL DESIGN: PAGE-AGNOSTIC EXTRACTION
        
        OLD (Page-Number-Dependent) ❌:
        - Page 1: Extract ALL fields (header + totals + items)
        - Pages 2-N: Extract ONLY items
        → Fragile: PO on page 2 footer → MISSED
        → Fragile: Totals on last page → MISSED
        
        NEW (Page-Agnostic) ✅:
        - Pass 1: ALL PAGES → Header fields
        - Pass 2: ALL PAGES → Totals fields
        - Pass 3: ALL PAGES → Items
        → Robust: PO on any page → FOUND
        → Robust: Totals on any page → FOUND
        
        Strategy:
        1. Concatenate all pages into a single tall image
        2. Send complete document to each extraction pass
        3. Model sees entire invoice context
        4. No page-number assumptions
        
        Args:
            images: List of PIL Images (one per page)
            use_two_pass: Use three-pass extraction (header, totals, items)
            temperature: Model temperature
        
        Returns:
            Tuple of (merged_data_dict, metadata_dict)
        """
        from schema import get_header_prompt, get_totals_prompt, get_items_prompt
        
        if not images:
            return {'error': 'No images provided'}, {}
        
        page_count = len(images)
        
        print("\n" + "="*80)
        print(f"📄 MULTI-PAGE EXTRACTION MODE ({page_count} pages)")
        print("="*80)
        print("📋 Strategy: PAGE-AGNOSTIC (all pages sent to each pass)")
        print("="*80)
        
        # ════════════════════════════════════════════════════════════
        # CONCATENATE ALL PAGES INTO SINGLE TALL IMAGE
        # ════════════════════════════════════════════════════════════
        print(f"\n🔗 Concatenating {page_count} pages into single document...")
        
        # Get dimensions
        widths = [img.width for img in images]
        heights = [img.height for img in images]
        max_width = max(widths)
        total_height = sum(heights)
        
        # Create tall canvas
        combined_image = Image.new('RGB', (max_width, total_height), 'white')
        
        # Paste pages vertically
        y_offset = 0
        for idx, img in enumerate(images):
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Center horizontally if narrower than max_width
            x_offset = (max_width - img.width) // 2
            combined_image.paste(img, (x_offset, y_offset))
            y_offset += img.height
            
            print(f"   Page {idx + 1}: {img.width}x{img.height} at y={y_offset - img.height}")
        
        print(f"✅ Combined image: {combined_image.width}x{combined_image.height}")
        
        # ════════════════════════════════════════════════════════════
        # THREE-PASS EXTRACTION: ALL PAGES TO EACH PASS
        # ════════════════════════════════════════════════════════════
        merged_data = {}
        pass_metadata = {}
        
        # Pass 1: Header fields from ENTIRE DOCUMENT
        print("\n📋 Pass 1: Extracting header fields from ALL PAGES...")
        header_system, header_user = get_header_prompt()
        
        header_data, header_response = self.extract_invoice(
            combined_image,
            header_system,
            header_user,
            temperature=temperature,
            max_tokens=1000
        )
        
        if 'error' in header_data:
            return {
                'error': f"Pass 1 (Header) failed: {header_data['error']}",
                'failed_pass': 'header',
                'partial_results': {}
            }, {'pass_1': header_response}
        
        merged_data.update(header_data)
        pass_metadata['pass_1_header'] = {
            'fields_extracted': len(header_data),
            'pages_used': page_count
        }
        print(f"✅ Pass 1 complete: {len(header_data)} header fields extracted from {page_count} pages")
        
        # Pass 2: Totals fields from ENTIRE DOCUMENT
        print("\n💰 Pass 2: Extracting totals fields from ALL PAGES...")
        totals_system, totals_user = get_totals_prompt()
        
        totals_data, totals_response = self.extract_invoice(
            combined_image,
            totals_system,
            totals_user,
            temperature=temperature,
            max_tokens=1000
        )
        
        if 'error' in totals_data:
            return {
                'error': f"Pass 2 (Totals) failed: {totals_data['error']}",
                'failed_pass': 'totals',
                'partial_results': merged_data.copy()
            }, {'pass_1': header_response, 'pass_2': totals_response}
        
        merged_data.update(totals_data)
        pass_metadata['pass_2_totals'] = {
            'fields_extracted': len(totals_data),
            'pages_used': page_count
        }
        print(f"✅ Pass 2 complete: {len(totals_data)} totals fields extracted from {page_count} pages")
        
        # Pass 3: Line items from ENTIRE DOCUMENT
        print("\n📦 Pass 3: Extracting line items from ALL PAGES...")
        items_system, items_user = get_items_prompt()
        
        items_data, items_response = self.extract_invoice(
            combined_image,
            items_system,
            items_user,
            temperature=temperature,
            max_tokens=4000  # Increased for multi-page items
        )
        
        if 'error' in items_data:
            return {
                'error': f"Pass 3 (Items) failed: {items_data['error']}",
                'failed_pass': 'items',
                'partial_results': merged_data.copy()
            }, {'pass_1': header_response, 'pass_2': totals_response, 'pass_3': items_response}
        
        # Merge items array
        all_items = items_data.get('items', [])
        
        # ════════════════════════════════════════════════════════════
        # DUPLICATE DETECTION
        # ════════════════════════════════════════════════════════════
        # Some OCR may repeat rows at page boundaries
        print(f"\n🔍 Checking for duplicate items...")
        
        seen_items = set()
        unique_items = []
        duplicate_count = 0
        
        for item in all_items:
            batch = (item.get('Batch') or '').strip().lower()
            desc = (item.get('description') or '').strip().lower()
            qty = str(item.get('quantity', '')).strip()
            
            # Use (description, batch, quantity) as uniqueness key
            item_key = (desc, batch, qty)
            
            if item_key in seen_items and desc and batch:
                duplicate_count += 1
                print(f"   ⚠️  Skipping duplicate: {item.get('description')[:40]} | Batch: {item.get('Batch')} | Qty: {qty}")
            else:
                unique_items.append(item)
                if desc and batch:
                    seen_items.add(item_key)
        
        merged_data['items'] = unique_items
        pass_metadata['pass_3_items'] = {
            'items_extracted': len(all_items),
            'items_unique': len(unique_items),
            'duplicates_skipped': duplicate_count,
            'pages_used': page_count
        }
        
        print(f"✅ Pass 3 complete: {len(all_items)} items extracted, {len(unique_items)} unique, {duplicate_count} duplicates skipped")
        
        print("\n" + "="*80)
        print(f"✅ THREE-PASS EXTRACTION COMPLETE (Page-Agnostic)")
        print(f"   Header fields: {pass_metadata['pass_1_header']['fields_extracted']}")
        print(f"   Totals fields: {pass_metadata['pass_2_totals']['fields_extracted']}")
        print(f"   Unique items: {pass_metadata['pass_3_items']['items_unique']}")
        print(f"   Pages processed: {page_count}")
        print("="*80 + "\n")
        
        metadata = {
            'passes': pass_metadata,
            'total_pages': page_count,
            'total_items': len(unique_items),
            'duplicates_skipped': duplicate_count,
            'extraction_strategy': 'page_agnostic'
        }
        
        return merged_data, metadata
