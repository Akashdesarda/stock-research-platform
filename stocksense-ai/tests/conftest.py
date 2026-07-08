"""Pytest configuration for stocksense-ai tests."""

import sys
from pathlib import Path

# Add project root to Python path so tests can import from app
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
