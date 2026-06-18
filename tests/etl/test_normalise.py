import sys
sys.path.insert(0, "src/etl")

from normaliser import normalize_year, normalize_ticker

# ── normalize_year ─────────────────────────────────────────────────────────────
def test_year_mar_space():    assert normalize_year("Mar 2014") == "2014-03"
def test_year_dec_space():    assert normalize_year("Dec 2012") == "2012-12"
def test_year_mar_dash():     assert normalize_year("Mar-23")   == "2023-03"
def test_year_mar_dash_long():assert normalize_year("Mar-2023") == "2023-03"
def test_year_fy24():         assert normalize_year("FY24")     == "2024-03"
def test_year_fy2024():       assert normalize_year("FY2024")   == "2024-03"
def test_year_int():          assert normalize_year("2023")     == "2023-03"
def test_year_already_norm(): assert normalize_year("2023-03")  == "2023-03"
def test_year_dec22():        assert normalize_year("Dec-22")   == "2022-12"
def test_year_jun23():        assert normalize_year("Jun-23")   == "2023-06"
def test_year_garbage():      assert normalize_year("xyz")      == "PARSE_ERROR"
def test_year_none():         assert normalize_year(None)       == "PARSE_ERROR"
def test_year_empty():        assert normalize_year("")         == "PARSE_ERROR"
def test_year_mar13():        assert normalize_year("Mar-13")   == "2013-03"
def test_year_jan2020():      assert normalize_year("Jan 2020") == "2020-01"

# ── normalize_ticker ───────────────────────────────────────────────────────────
def test_ticker_upper():      assert normalize_ticker("tcs")        == "TCS"
def test_ticker_strip():      assert normalize_ticker("  TCS  ")    == "TCS"
def test_ticker_hyphen():     assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"
def test_ticker_ampersand():  assert normalize_ticker("M&M")        == "M&M"
def test_ticker_none():       assert normalize_ticker(None)         == ""
def test_ticker_too_short():  assert normalize_ticker("A")          == ""