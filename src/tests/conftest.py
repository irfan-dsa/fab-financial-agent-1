"""
Pytest configuration and shared fixtures for FAB Financial Agent tests.
"""
import pytest
import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_financial_data():
    """Provide sample financial data for testing."""
    return {
        "net_profit_q1_2025": 5135,
        "net_profit_q1_2024": 4161,
        "shareholder_equity_q1_2025": 127331,
        "total_assets_q1_2025": 1306568,
    }
