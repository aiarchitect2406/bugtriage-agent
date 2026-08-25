"""Payment Gateway Service with order checkout and tax calculation."""

from typing import Dict, Any, Optional

def calculate_tax(shipping_address: Optional[Dict[str, Any]], subtotal: float) -> float:
    """Calculates sales tax based on the shipping address state.
    
    BUG: If shipping_address is None (e.g., digital good or missing address),
    accessing shipping_address['state'] raises TypeError / AttributeError.
    """
    # Intentional bug: does not handle None shipping_address safely
    state = shipping_address.get("state", "CA") if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA" if shipping_address else "CA"
    tax_rates = {
        "CA": 0.0825,
        "NY": 0.08875,
        "TX": 0.0625,
        "WA": 0.0650
    }
    rate = tax_rates.get(state, 0.05)
    return round(subtotal * rate, 2)

def process_checkout(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Processes a user checkout order.

    Args:
        payload: Order details including user_id, items, and optional shipping_address.

    Returns:
        Dict[str, Any]: Checkout result with status, total_amount, and order_id.
    """
    user_id = payload.get("user_id")
    items = payload.get("items", [])
    shipping_address = payload.get("shipping_address")

    if not user_id or not items:
        return {"status": "ERROR", "message": "Missing required user_id or items"}

    # Calculate item subtotal
    subtotal = sum(item.get("price", 10.0) * item.get("quantity", 1) for item in items)

    # Calculate tax - triggers bug if shipping_address is None
    tax = calculate_tax(shipping_address, subtotal)
    total_amount = round(subtotal + tax, 2)

    return {
        "status": "SUCCESS",
        "order_id": f"ORD-{user_id}-9942",
        "subtotal": subtotal,
        "tax": tax,
        "total_amount": total_amount,
        "message": "Order placed successfully"
    }
