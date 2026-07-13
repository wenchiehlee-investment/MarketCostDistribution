import sys
import pandas as pd
import numpy as np
from pathlib import Path
from src.data_loader import DataLoader
from src.simulator import CostSimulator
import argparse

sys.stdout.reconfigure(encoding='utf-8')

class VolumeProfile:
    """Standard Volume Profile baseline with NO decay."""
    def __init__(self, bin_size: float = 0.5):
        self.bin_size = bin_size
        self.distribution = {}
        
    def get_bin(self, price: float) -> float:
        return round(price / self.bin_size) * self.bin_size
        
    def add_volume(self, low: float, high: float, vwap: float, volume: float):
        if pd.isna(low) or pd.isna(high) or high <= low:
            bin_center = self.get_bin(vwap)
            self.distribution[bin_center] = self.distribution.get(bin_center, 0.0) + volume
            return
            
        start_bin = self.get_bin(low)
        end_bin = self.get_bin(high)
        bins = []
        curr = start_bin
        while curr <= end_bin:
            bins.append(curr)
            curr = round((curr + self.bin_size) / self.bin_size) * self.bin_size
            
        if not bins:
            bin_center = self.get_bin(vwap)
            self.distribution[bin_center] = self.distribution.get(bin_center, 0.0) + volume
            return
            
        half_range = (high - low) / 2.0
        raw_weights = [max(0.0, 1.0 - abs(b - vwap) / (half_range if half_range > 0 else 1.0)) for b in bins]
        total_raw = sum(raw_weights)
        if total_raw == 0:
            raw_weights = [1.0] * len(bins)
            total_raw = len(bins)
            
        for b, rw in zip(bins, raw_weights):
            self.distribution[b] = self.distribution.get(b, 0.0) + (rw / total_raw) * volume

def find_peaks(distribution: dict, bin_size: float, top_n: int = 3, min_fraction: float = 0.01) -> list:
    """Finds the local maxima (peaks) in the distribution."""
    if not distribution:
        return []
    total_val = sum(distribution.values())
    if total_val == 0:
        return []
        
    peaks = []
    prices = sorted(distribution.keys())
    for i, p in enumerate(prices):
        w = distribution[p]
        if (w / total_val) < min_fraction:
            continue
        prev_w = distribution[prices[i-1]] if i > 0 else 0.0
        next_w = distribution[prices[i+1]] if i < len(prices) - 1 else 0.0
        if w >= prev_w and w >= next_w:
            peaks.append((p, w))
            
    peaks = sorted(peaks, key=lambda x: x[1], reverse=True)[:top_n]
    return [p[0] for p in peaks]

def backtest_stock(symbol: str, warmup_days: int = 250) -> dict:
    loader = DataLoader()
    df_prices = loader.load_daily_prices(symbol)
    shares_outstanding = loader.load_shares_outstanding(symbol)
    shareholder_concentration = loader.load_weekly_shareholder_concentration(symbol)
    
    bin_size = 1.0 if symbol in ["2330", "2454", "3034"] else 0.5
    
    # 1. Simulate Cost Simulator (Dual-Pool)
    cost_sim = CostSimulator(bin_size=bin_size)
    cost_history = cost_sim.run_daily_simulation(
        df_prices, 
        shares_outstanding, 
        [], 
        shareholder_concentration=shareholder_concentration,
        stock_code=symbol
    )
    
    # 2. Simulate standard Volume Profile baseline (No decay)
    vp = VolumeProfile(bin_size=bin_size)
    vp_history = []
    for idx, row in df_prices.iterrows():
        # Estimate VWAP
        h, l, c = row["High"], row["Low"], row["Close"]
        vwap = (h + l + c) / 3.0 if (pd.notna(h) and pd.notna(l) and h > 0) else c
        vp.add_volume(l, h, vwap, row["Volume"])
        vp_history.append(dict(vp.distribution))
        
    # Metrics containers
    cost_metrics = {"touches": 0, "bounces": 0, "ret_5d": [], "ret_10d": [], "ret_20d": [], "mae_5d": []}
    vp_metrics = {"touches": 0, "bounces": 0, "ret_5d": [], "ret_10d": [], "ret_20d": [], "mae_5d": []}
    
    # Walk-forward validation loop
    # We test S/R on day 'idx' using distribution at day 'idx-1'
    N = len(df_prices)
    for idx in range(warmup_days, N - 20):
        current_row = df_prices.iloc[idx]
        prev_close = df_prices.iloc[idx - 1]["Close"]
        
        low = current_row["Low"]
        high = current_row["High"]
        
        # Test Cost Simulator peaks
        cost_dist_prev = cost_history[idx - 1]["Distribution"]
        cost_peaks = find_peaks(cost_dist_prev, bin_size, top_n=3)
        for peak in cost_peaks:
            # Support touch: price was above peak yesterday, and touches peak today
            if prev_close >= peak and low <= peak <= high:
                cost_metrics["touches"] += 1
                
                # Check forward prices
                future_prices = df_prices.iloc[idx:idx+20]
                closes_5d = future_prices.iloc[0:5]["Close"].values
                lows_5d = future_prices.iloc[0:5]["Low"].values
                
                # Bounce defined as: max close price in next 5 days goes up >= 2% from peak
                if len(closes_5d) > 0 and max(closes_5d) >= peak * 1.02:
                    cost_metrics["bounces"] += 1
                    
                # Forward returns
                cost_metrics["ret_5d"].append((df_prices.iloc[idx+5]["Close"] - peak) / peak)
                cost_metrics["ret_10d"].append((df_prices.iloc[idx+10]["Close"] - peak) / peak)
                cost_metrics["ret_20d"].append((df_prices.iloc[idx+20]["Close"] - peak) / peak)
                
                # MAE (Maximum Adverse Excursion) within 5 days
                cost_metrics["mae_5d"].append(min((lows_5d - peak) / peak) if len(lows_5d) > 0 else 0.0)
                
        # Test Volume Profile peaks
        vp_dist_prev = vp_history[idx - 1]
        vp_peaks = find_peaks(vp_dist_prev, bin_size, top_n=3)
        for peak in vp_peaks:
            if prev_close >= peak and low <= peak <= high:
                vp_metrics["touches"] += 1
                
                future_prices = df_prices.iloc[idx:idx+20]
                closes_5d = future_prices.iloc[0:5]["Close"].values
                lows_5d = future_prices.iloc[0:5]["Low"].values
                
                if len(closes_5d) > 0 and max(closes_5d) >= peak * 1.02:
                    vp_metrics["bounces"] += 1
                    
                vp_metrics["ret_5d"].append((df_prices.iloc[idx+5]["Close"] - peak) / peak)
                vp_metrics["ret_10d"].append((df_prices.iloc[idx+10]["Close"] - peak) / peak)
                vp_metrics["ret_20d"].append((df_prices.iloc[idx+20]["Close"] - peak) / peak)
                vp_metrics["mae_5d"].append(min((lows_5d - peak) / peak) if len(lows_5d) > 0 else 0.0)
                
    return {
        "symbol": symbol,
        "cost": cost_metrics,
        "vp": vp_metrics
    }

def print_summary(results_list: list):
    print("\n" + "="*85)
    print(f"【多個股量化持股成本 vs. 累積成交量分布 (Volume Profile) 閉環回測總表】")
    print("="*85)
    print(f"{'標的':<6} | {'模型':<16} | {'觸碰次數':<8} | {'5日反彈率':<9} | {'5日均報酬':<9} | {'20日均報酬':<9} | {'5日最大跌幅 (MAE)':<14}")
    print("-"*85)
    
    total_cost_touches = 0
    total_cost_bounces = 0
    total_vp_touches = 0
    total_vp_bounces = 0
    
    cost_all_ret_5d = []
    cost_all_ret_20d = []
    cost_all_mae = []
    vp_all_ret_5d = []
    vp_all_ret_20d = []
    vp_all_mae = []
    
    for r in results_list:
        symbol = r["symbol"]
        
        # Cost Sim
        c = r["cost"]
        c_touch = c["touches"]
        c_bounce_rate = (c["bounces"] / c_touch * 100) if c_touch > 0 else 0.0
        c_ret5 = np.mean(c["ret_5d"]) * 100 if c["ret_5d"] else 0.0
        c_ret20 = np.mean(c["ret_20d"]) * 100 if c["ret_20d"] else 0.0
        c_mae = np.mean(c["mae_5d"]) * 100 if c["mae_5d"] else 0.0
        
        print(f"{symbol:<6} | {'Cost Simulator':<16} | {c_touch:<8} | {c_bounce_rate:.2f}% | {c_ret5:+.2f}%   | {c_ret20:+.2f}%   | {c_mae:.2f}%")
        
        # Volume Profile
        v = r["vp"]
        v_touch = v["touches"]
        v_bounce_rate = (v["bounces"] / v_touch * 100) if v_touch > 0 else 0.0
        v_ret5 = np.mean(v["ret_5d"]) * 100 if v["ret_5d"] else 0.0
        v_ret20 = np.mean(v["ret_20d"]) * 100 if v["ret_20d"] else 0.0
        v_mae = np.mean(v["mae_5d"]) * 100 if v["mae_5d"] else 0.0
        
        print(f"{'':<6} | {'Volume Profile':<16} | {v_touch:<8} | {v_bounce_rate:.2f}% | {v_ret5:+.2f}%   | {v_ret20:+.2f}%   | {v_mae:.2f}%")
        print("-"*85)
        
        total_cost_touches += c_touch
        total_cost_bounces += c["bounces"]
        total_vp_touches += v_touch
        total_vp_bounces += v["bounces"]
        
        cost_all_ret_5d.extend(c["ret_5d"])
        cost_all_ret_20d.extend(c["ret_20d"])
        cost_all_mae.extend(c["mae_5d"])
        
        vp_all_ret_5d.extend(v["ret_5d"])
        vp_all_ret_20d.extend(v["ret_20d"])
        vp_all_mae.extend(v["mae_5d"])
        
    # Aggregate Summary
    agg_c_bounce = (total_cost_bounces / total_cost_touches * 100) if total_cost_touches > 0 else 0.0
    agg_c_ret5 = np.mean(cost_all_ret_5d) * 100 if cost_all_ret_5d else 0.0
    agg_c_ret20 = np.mean(cost_all_ret_20d) * 100 if cost_all_ret_20d else 0.0
    agg_c_mae = np.mean(cost_all_mae) * 100 if cost_all_mae else 0.0
    
    agg_v_bounce = (total_vp_bounces / total_vp_touches * 100) if total_vp_touches > 0 else 0.0
    agg_v_ret5 = np.mean(vp_all_ret_5d) * 100 if vp_all_ret_5d else 0.0
    agg_v_ret20 = np.mean(vp_all_ret_20d) * 100 if vp_all_ret_20d else 0.0
    agg_v_mae = np.mean(vp_all_mae) * 100 if vp_all_mae else 0.0
    
    print(f"{'總計':<6} | {'Cost Simulator':<16} | {total_cost_touches:<8} | {agg_c_bounce:.2f}% | {agg_c_ret5:+.2f}%   | {agg_c_ret20:+.2f}%   | {agg_c_mae:.2f}%")
    print(f"{'':<6} | {'Volume Profile':<16} | {total_vp_touches:<8} | {agg_v_bounce:.2f}% | {agg_v_ret5:+.2f}%   | {agg_v_ret20:+.2f}%   | {agg_v_mae:.2f}%")
    print("="*85 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, default="2330,2454,2382,8299,2308", help="Comma separated stock symbols or 'all'")
    args = parser.parse_args()
    
    if args.symbols.strip().lower() == "all":
        focus_csv = Path("C:/Users/WJLEE/SynologyDrive/NAS/github.com/biztrends.TW/StockID_TWSE_TPEX_focus.csv")
        if not focus_csv.exists():
            print(f"Error: Focus list CSV not found at {focus_csv}")
            sys.exit(1)
        df_focus = pd.read_csv(focus_csv, dtype={"代號": str})
        symbols_list = df_focus["代號"].str.strip().tolist()
    else:
        symbols_list = [s.strip() for s in args.symbols.split(",") if s.strip()]
        
    results = []
    for sym in symbols_list:
        try:
            print(f"Running backtest for {sym}...")
            results.append(backtest_stock(sym))
        except Exception as e:
            print(f"Error running backtest for {sym}: {e}")
        
    print_summary(results)
