"""Pytest configuration and test environment setup."""

import sys
import os

# Inject test fixtures path into sys.path so unit/integration tests can import mock services
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
if FIXTURES_DIR not in sys.path:
    sys.path.insert(0, FIXTURES_DIR)
