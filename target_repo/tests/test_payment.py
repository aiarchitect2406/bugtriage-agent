"""Base test suite for payment gateway."""

import pytest
from target_repo.services.payment_gateway import process_checkout

def test_successful_checkout_with_address():
    """Verifies that checkout succeeds when valid address is provided."""
    payload = {
        "user_id": "U-1001",
        "items": [{"name": "Laptop", "price": 1000.0, "quantity": 1}],
        "shipping_address": {"state": "CA", "zip": "94105"}
    }
    result = process_checkout(payload)
    assert result["status"] == "SUCCESS"
    assert result["tax"] == 82.50
    assert result["total_amount"] == 1082.50

def test_missing_user_or_items():
    """Verifies rejection on missing user_id."""
    payload = {"items": [{"name": "Book", "price": 10.0, "quantity": 1}]}
    result = process_checkout(payload)
    assert result["status"] == "ERROR"
