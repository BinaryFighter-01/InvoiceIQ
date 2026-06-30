"""
Comprehensive GST Enrichment for Variable Invoice Formats
Handles all edge cases for pharma invoices
"""

from typing import Dict, List, Any, Optional


def round_to_2(value: float) -> float:
    """Round to 2 decimal places."""
    if value is None:
        return 0.0
    return round(float(value), 2)


def enrich_item_gst(item: Dict[str, Any], is_intra_state: bool = True) -> Dict[str, Any]:
    """
    Enrich item-level GST fields using hierarchical logic.
    
    Hierarchy:
    1. Use invoice values if present (cgst_amount, sgst_amount explicitly shown)
    2. Calculate from GST_AMT if present
    3. Calculate from Value × Gst% if both present
    4. Mark source for transparency
    
    Args:
        item: Item dictionary
        is_intra_state: True for CGST+SGST, False for IGST
    
    Returns:
        Enriched item dictionary with _gst_source marker
    """
    
    # Extract values - handle None
    value = float(item.get('Value', 0) or 0)
    gst_percent = float(item.get('Gst%', 0) or 0)
    gst_amt = item.get('GST_AMT')
    if gst_amt is not None and gst_amt != '':
        gst_amt = float(gst_amt)
    else:
        gst_amt = None
    cgst_amt_existing = item.get('cgst_amount')
    sgst_amt_existing = item.get('sgst_amount')
    igst_amt_existing = item.get('igst_amount')
    
    # Case 1: Invoice already has explicit CGST/SGST/IGST amounts
    if cgst_amt_existing is not None and sgst_amt_existing is not None:
        # Keep invoice values
        item['_gst_source'] = 'invoice'
        return item
    
    if igst_amt_existing is not None and igst_amt_existing > 0:
        # Keep invoice values
        item['_gst_source'] = 'invoice'
        return item
    
    # Case 2: Calculate from GST_AMT (if present)
    if gst_amt is not None and gst_amt > 0 and gst_percent > 0:
        if is_intra_state:
            # Split GST_AMT into CGST and SGST
            cgst_rate = round_to_2(gst_percent / 2)
            sgst_rate = round_to_2(gst_percent / 2)
            cgst_amount = round_to_2(gst_amt / 2)
            sgst_amount = round_to_2(gst_amt - cgst_amount)  # Ensure sum equals GST_AMT
            
            item['cgst_rate'] = cgst_rate
            item['cgst_amount'] = cgst_amount
            item['sgst_rate'] = sgst_rate
            item['sgst_amount'] = sgst_amount
            item['igst_rate'] = 0
            item['igst_amount'] = 0
            item['_gst_source'] = 'calculated_from_gst_amt'
        else:
            # Inter-state: All GST_AMT goes to IGST
            item['cgst_rate'] = 0
            item['cgst_amount'] = 0
            item['sgst_rate'] = 0
            item['sgst_amount'] = 0
            item['igst_rate'] = gst_percent
            item['igst_amount'] = gst_amt
            item['_gst_source'] = 'calculated_from_gst_amt'
        
        return item
    
    # Case 3: Calculate from Value × Gst%
    if value > 0 and gst_percent > 0:
        gst_amt_calculated = round_to_2(value * gst_percent / 100)
        
        # Store calculated GST_AMT if not present
        if gst_amt is None:
            item['GST_AMT'] = gst_amt_calculated
        
        if is_intra_state:
            cgst_rate = round_to_2(gst_percent / 2)
            sgst_rate = round_to_2(gst_percent / 2)
            cgst_amount = round_to_2(gst_amt_calculated / 2)
            sgst_amount = round_to_2(gst_amt_calculated - cgst_amount)
            
            item['cgst_rate'] = cgst_rate
            item['cgst_amount'] = cgst_amount
            item['sgst_rate'] = sgst_rate
            item['sgst_amount'] = sgst_amount
            item['igst_rate'] = 0
            item['igst_amount'] = 0
            item['_gst_source'] = 'calculated_from_value_gst_percent'
        else:
            # Inter-state
            item['cgst_rate'] = 0
            item['cgst_amount'] = 0
            item['sgst_rate'] = 0
            item['sgst_amount'] = 0
            item['igst_rate'] = gst_percent
            item['igst_amount'] = gst_amt_calculated
            item['_gst_source'] = 'calculated_from_value_gst_percent'
        
        return item
    
    # Case 4: No GST information available
    item['_gst_source'] = 'not_calculated'
    return item


def enrich_totals_gst(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich invoice-level totals GST fields.
    
    Fixes common issues:
    - total_gst_rate = 10 when it should be 5 (confusion between total and component)
    - CGST/SGST rates should be HALF of total GST rate
    
    Args:
        data: Invoice data dictionary
    
    Returns:
        Enriched data dictionary
    """
    total_gst_rate = data.get('total_gst_rate', 0) or 0
    total_cgst_rate = data.get('total_cgst_rate', 0) or 0
    total_sgst_rate = data.get('total_sgst_rate', 0) or 0
    total_igst_rate = data.get('total_igst_rate', 0) or 0
    
    # Detect and fix common error: total_gst_rate = 10, cgst = 5, sgst = 5
    # This is wrong: total should be 5, cgst should be 2.5, sgst should be 2.5
    if total_cgst_rate > 0 and total_sgst_rate > 0:
        # Intra-state transaction
        if total_cgst_rate + total_sgst_rate != total_gst_rate:
            # Rates don't add up - likely cgst and sgst are correctly half each
            # So total_gst_rate should be cgst + sgst
            corrected_total = total_cgst_rate + total_sgst_rate
            if corrected_total != total_gst_rate:
                print(f"⚠️  Correcting total_gst_rate: {total_gst_rate} → {corrected_total}")
                print(f"   CGST: {total_cgst_rate}%, SGST: {total_sgst_rate}%")
                data['total_gst_rate'] = corrected_total
                data['_gst_rate_corrected'] = True
    
    elif total_igst_rate > 0:
        # Inter-state transaction
        if total_gst_rate != total_igst_rate:
            print(f"⚠️  Correcting total_gst_rate: {total_gst_rate} → {total_igst_rate}")
            data['total_gst_rate'] = total_igst_rate
            data['_gst_rate_corrected'] = True
    
    return data


def determine_transaction_type(data: Dict[str, Any]) -> str:
    """
    Determine if transaction is intra-state or inter-state.
    
    Logic:
    1. Check if CGST/SGST amounts present → intra-state
    2. Check if IGST amounts present → inter-state
    3. Fallback: intra-state (most common)
    
    Returns:
        'intra-state' or 'inter-state'
    """
    # Check totals
    if data.get('total_cgst_amount') and data.get('total_cgst_amount') > 0:
        return 'intra-state'
    if data.get('total_igst_amount') and data.get('total_igst_amount') > 0:
        return 'inter-state'
    
    # Check first item
    items = data.get('items', [])
    if items:
        first_item = items[0]
        if first_item.get('cgst_amount') and first_item.get('cgst_amount') > 0:
            return 'intra-state'
        if first_item.get('igst_amount') and first_item.get('igst_amount') > 0:
            return 'inter-state'
    
    # Default to intra-state
    return 'intra-state'


def enrich_gst_comprehensive(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive GST enrichment for all invoice types.
    
    Process:
    1. Determine transaction type (intra/inter state)
    2. Fix totals GST rates if needed
    3. Enrich each item's GST fields
    4. Add transparency markers
    
    Args:
        data: Raw extracted invoice data
    
    Returns:
        Enriched data with calculated GST fields
    """
    print("\n" + "="*80)
    print("GST ENRICHMENT")
    print("="*80)
    
    # Step 1: Determine transaction type
    transaction_type = determine_transaction_type(data)
    is_intra_state = (transaction_type == 'intra-state')
    
    print(f"Transaction type: {transaction_type}")
    print(f"GST split: {'CGST + SGST' if is_intra_state else 'IGST'}")
    
    # Step 2: Fix totals GST rates
    data = enrich_totals_gst(data)
    
    # Step 3: Enrich each item
    items = data.get('items', [])
    if items:
        print(f"\nEnriching {len(items)} items...")
        for idx, item in enumerate(items, 1):
            item = enrich_item_gst(item, is_intra_state)
            items[idx - 1] = item
            
            # Log enrichment source
            source = item.get('_gst_source', 'unknown')
            if source != 'invoice':
                gst_amt = item.get('GST_AMT', 0) or 0
                print(f"  Item {idx}: {source} (GST: ₹{gst_amt:.2f})")
    
    print("="*80 + "\n")
    
    return data
