import sys, math
sys.path.insert(0, "src/analytics")
from cagr import compute_cagr
import numpy as np

def test_normal():
    val, flag = compute_cagr(100, 161.05, 5)
    assert flag == "OK"
    assert abs(val - 10.0) < 0.1

def test_turnaround():
    val, flag = compute_cagr(-100, 200, 5)
    assert flag == "TURNAROUND"
    assert val is np.nan or (val != val)  # nan check

def test_decline_to_loss():
    val, flag = compute_cagr(100, -50, 5)
    assert flag == "DECLINE_TO_LOSS"

def test_both_negative():
    val, flag = compute_cagr(-100, -50, 5)
    assert flag == "BOTH_NEGATIVE"

def test_zero_base():
    val, flag = compute_cagr(0, 100, 5)
    assert flag == "ZERO_BASE"

def test_insufficient():
    val, flag = compute_cagr(100, 200, 0)
    assert flag == "INSUFFICIENT"

def test_high_growth():
    val, flag = compute_cagr(100, 259.37, 10)
    assert flag == "OK"
    assert abs(val - 10.0) < 0.1

def test_negative_growth():
    val, flag = compute_cagr(200, 100, 5)
    assert flag == "OK"
    assert val < 0