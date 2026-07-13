import sys
import pandas as pd
import numpy as np
from pathlib import Path
from src.data_loader import DataLoader
from src.simulator import CostSimulator
import argparse

sys.stdout.reconfigure(encoding='utf-8')

def find_peaks(distribution: dict, bin_size: float, top_n: int = 3, min_weight: float = 0.01) -> list:
    """Finds the local maxima (peaks) in the cost distribution."""
    peaks = []
    prices = sorted(distribution.keys())
    for i, p in enumerate(prices):
        w = distribution[p]
        if w < min_weight:
            continue
        # Check if local maximum
        prev_w = distribution[prices[i-1]] if i > 0 else 0.0
        next_w = distribution[prices[i+1]] if i < len(prices) - 1 else 0.0
        if w >= prev_w and w >= next_w:
            peaks.append((p, w))
            
    # Sort by weight descending and take top N
    peaks = sorted(peaks, key=lambda x: x[1], reverse=True)[:top_n]
    return [p[0] for p in peaks]

def evaluate_closed_loop(symbol: str, warmup_days: int = 250) -> dict:
    loader = DataLoader()
    df_prices = loader.load_daily_prices(symbol)
    shares_outstanding = loader.load_shares_outstanding(symbol)
    
    # Run simulation day-by-day
    simulator = CostSimulator(bin_size=1.0 if symbol in ["2330", "2454", "3034"] else 0.5)
    history = simulator.run_daily_simulation(df_prices, shares_outstanding, [], stock_code=symbol)
    
    total_support_tests = 0
    successful_support_bounces = 0
    total_resistance_tests = 0
    successful_resistance_rejections = 0
    
    # We start testing after warmup period
    for idx in range(warmup_days, len(df_prices) - 5):
        current_row = df_prices.iloc[idx]
        prev_close = df_prices.iloc[idx - 1]["Close"]
        
        # Get peaks from the previous day's distribution
        prev_dist = history[idx - 1]["Distribution"]
        peaks = find_peaks(prev_dist, simulator.bin_size)
        
        low = current_row["Low"]
        high = current_row["High"]
        
        for peak in peaks:
            # Check if price touched the peak today
            if low <= peak <= high:
                # 1. Support Test (Touched from above)
                if prev_close >= peak:
                    total_support_tests += 1
                    # Success: price remains above peak in the next 3 days
                    future_closes = df_prices.iloc[idx:idx+3]["Close"].values
                    if all(fc >= peak * 0.985 for fc in future_closes): # Allow 1.5% buffer
                        successful_support_bounces += 1
                        
                # 2. Resistance Test (Touched from below)
                elif prev_close < peak:
                    total_resistance_tests += 1
                    # Success: price fails to break above peak in the next 3 days
                    future_closes = df_prices.iloc[idx:idx+3]["Close"].values
                    if all(fc <= peak * 1.015 for fc in future_closes): # Allow 1.5% buffer
                        successful_resistance_rejections += 1
                        
    support_accuracy = successful_support_bounces / total_support_tests if total_support_tests > 0 else 0.0
    resistance_accuracy = successful_resistance_rejections / total_resistance_tests if total_resistance_tests > 0 else 0.0
    
    total_tests = total_support_tests + total_resistance_tests
    total_success = successful_support_bounces + successful_resistance_rejections
    overall_accuracy = total_success / total_tests if total_tests > 0 else 0.0
    
    return {
        "symbol": symbol,
        "total_support_tests": total_support_tests,
        "successful_support_bounces": successful_support_bounces,
        "support_accuracy": support_accuracy,
        "total_resistance_tests": total_resistance_tests,
        "successful_resistance_rejections": successful_resistance_rejections,
        "resistance_accuracy": resistance_accuracy,
        "total_tests": total_tests,
        "overall_accuracy": overall_accuracy
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="8299", help="Stock symbol to evaluate")
    args = parser.parse_args()
    
    res = evaluate_closed_loop(args.symbol)
    print(f"\n==========================================")
    print(f"【籌碼持股成本閉環驗證結果 - {res['symbol']}】")
    print(f"==========================================")
    print(f"支撐回測次數 (Support Tests): {res['total_support_tests']}")
    print(f"支撐反彈成功次數: {res['successful_support_bounces']}")
    print(f"支撐預測準確率 (Support Accuracy): {res['support_accuracy']*100:.2f}%")
    print(f"------------------------------------------")
    print(f"壓力回測次數 (Resistance Tests): {res['total_resistance_tests']}")
    print(f"壓力受阻成功次數: {res['successful_resistance_rejections']}")
    print(f"壓力預測準確率 (Resistance Accuracy): {res['resistance_accuracy']*100:.2f}%")
    print(f"------------------------------------------")
    print(f"總測試次數 (Total S/R Tests): {res['total_tests']}")
    print(f"整體預測準確率 (Overall Accuracy): {res['overall_accuracy']*100:.2f}%")
    print(f"==========================================\n")
