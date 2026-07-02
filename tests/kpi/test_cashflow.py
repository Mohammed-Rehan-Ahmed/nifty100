import sys
sys.path.insert(0, "src/analytics")
from cashflow_kpis import classify_pattern, cfo_quality, capex_category

def test_reinvestor():
    assert classify_pattern(100, -50, -30) == "Reinvestor"

def test_distress():
    assert classify_pattern(-50, -10, 100) == "Distress"

def test_asset_seller():
    assert classify_pattern(100, 50, -30) == "Asset Seller"

def test_cfo_quality_high():
    assert cfo_quality(1.2) == "High Quality Earnings"

def test_cfo_quality_moderate():
    assert cfo_quality(0.7) == "Moderate Quality"

def test_cfo_quality_accrual():
    assert cfo_quality(0.3) == "Accrual Risk"

def test_capex_asset_light():
    assert capex_category(2.0) == "Asset Light"

def test_capex_intensive():
    assert capex_category(9.0) == "Capital Intensive"