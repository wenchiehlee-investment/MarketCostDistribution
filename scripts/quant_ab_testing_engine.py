import sys
import pandas as pd
import numpy as np
import math
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

def mcnemar_test(model_a_results: list, model_b_results: list) -> dict:
    """Computes McNemar's test for paired binary outcomes."""
    assert len(model_a_results) == len(model_b_results)
    a = b = c = d = 0
    for ra, rb in zip(model_a_results, model_b_results):
        if ra and rb:
            a += 1
        elif ra and not rb:
            b += 1
        elif not ra and rb:
            c += 1
        else:
            d += 1
            
    if b + c == 0:
        chi2 = 0.0
        p_val = 1.0
    else:
        chi2 = (abs(b - c) - 1.0)**2 / (b + c)
        p_val = 1.0 - math.erf(math.sqrt(chi2 / 2.0))
        
    return {
        "contingency_table": {"a": a, "b": b, "c": c, "d": d},
        "chi2": chi2,
        "p_value": p_val,
        "significant": p_val < 0.05
    }

def wilcoxon_test(x: list, y: list) -> dict:
    """Computes Wilcoxon Signed-Rank test for paired samples."""
    assert len(x) == len(y)
    diffs = [xi - yi for xi, yi in zip(x, y) if xi - yi != 0.0]
    n = len(diffs)
    if n < 10:  # Too small for normal approximation
        return {"w_statistic": 0.0, "p_value": 1.0, "significant": False}
        
    sorted_diffs = sorted(diffs, key=abs)
    ranks = []
    i = 0
    while i < n:
        j = i
        while j < n - 1 and abs(sorted_diffs[j]) == abs(sorted_diffs[j+1]):
            j += 1
        mean_rank = sum(range(i+1, j+2)) / (j - i + 1)
        for _ in range(i, j+1):
            ranks.append(mean_rank)
        i = j + 1
        
    w_plus = 0.0
    w_minus = 0.0
    for d, r in zip(sorted_diffs, ranks):
        if d > 0:
            w_plus += r
        else:
            w_minus += r
            
    w_stat = min(w_plus, w_minus)
    expected_w = n * (n + 1) / 4.0
    var_w = n * (n + 1) * (2 * n + 1) / 24.0
    
    # Tie correction
    abs_diffs = [abs(d) for d in diffs]
    unique_vals = set(abs_diffs)
    if len(unique_vals) < n:
        tie_correction = 0.0
        for val in unique_vals:
            t = abs_diffs.count(val)
            if t > 1:
                tie_correction += (t**3 - t)
        var_w -= tie_correction / 48.0
        
    z_stat = (w_stat - expected_w) / math.sqrt(var_w) if var_w > 0 else 0.0
    p_val = 1.0 - math.erf(abs(z_stat) / math.sqrt(2.0))
    return {
        "w_statistic": w_stat,
        "z_statistic": z_stat,
        "p_value": p_val,
        "significant": p_val < 0.05
    }

def calculate_portfolio_metrics(trade_signals: list) -> dict:
    """
    Constructs a daily portfolio equity curve and calculates standard quant metrics.
    trade_signals: list of dicts: {"trade_dates": list of dates, "daily_returns": list of daily returns}
    """
    if not trade_signals:
        return {"return": 0.0, "vol": 0.0, "sharpe": 0.0, "sortino": 0.0, "mdd": 0.0, "pf": 0.0}
        
    # Map dates to daily returns of active trades
    daily_active_trades = {}
    for sig in trade_signals:
        for d, ret in zip(sig.get("trade_dates", []), sig.get("daily_returns", [])):
            if d not in daily_active_trades:
                daily_active_trades[d] = []
            daily_active_trades[d].append(ret)
            
    if not daily_active_trades:
        return {"return": 0.0, "vol": 0.0, "sharpe": 0.0, "sortino": 0.0, "mdd": 0.0, "pf": 0.0}
        
    sorted_dates = sorted(daily_active_trades.keys())
    portfolio_daily_returns = np.array([np.mean(daily_active_trades[d]) for d in sorted_dates])
    
    # Calculate metrics
    mean_ret = np.mean(portfolio_daily_returns)
    std_ret = np.std(portfolio_daily_returns)
    
    ann_return = mean_ret * 252
    ann_vol = std_ret * math.sqrt(252)
    
    sharpe = (ann_return / ann_vol) if ann_vol > 0 else 0.0
    
    # Downside deviation for Sortino
    neg_rets = portfolio_daily_returns[portfolio_daily_returns < 0]
    downside_std = np.std(neg_rets) * math.sqrt(252) if len(neg_rets) > 0 else 0.0
    sortino = (ann_return / downside_std) if downside_std > 0 else 0.0
    
    # Max Drawdown
    equity = np.cumprod(1.0 + portfolio_daily_returns)
    peaks = np.maximum.accumulate(equity)
    drawdowns = (equity - peaks) / peaks
    mdd = np.min(drawdowns) if len(drawdowns) > 0 else 0.0
    
    # Profit Factor
    gross_profits = np.sum(portfolio_daily_returns[portfolio_daily_returns > 0])
    gross_losses = np.sum(np.abs(portfolio_daily_returns[portfolio_daily_returns < 0]))
    pf = (gross_profits / gross_losses) if gross_losses > 0 else 1.0
    
    return {
        "return": ann_return,
        "vol": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "mdd": mdd,
        "pf": pf
    }

def backtest_single_stock(symbol: str, warmup_days: int = 250) -> dict:
    loader = DataLoader()
    try:
        df_prices = loader.load_daily_prices(symbol)
        shares_outstanding = loader.load_shares_outstanding(symbol)
        shareholder_concentration = loader.load_weekly_shareholder_concentration(symbol)
    except Exception:
        return None
        
    bin_size = 1.0 if symbol in ["2330", "2454", "3034"] else 0.5
    
    # 1. Run Baseline (Volume Profile)
    vp = VolumeProfile(bin_size=bin_size)
    vp_history = []
    for idx, row in df_prices.iterrows():
        h, l, c = row["High"], row["Low"], row["Close"]
        vwap = (h + l + c) / 3.0 if (pd.notna(h) and pd.notna(l) and h > 0) else c
        vp.add_volume(l, h, vwap, row["Volume"])
        vp_history.append(dict(vp.distribution))
        
    # 2. Run Cost Model v1 (Single Pool)
    cost_v1 = CostSimulator(bin_size=bin_size, model_type="single_pool")
    v1_history = cost_v1.run_daily_simulation(df_prices, shares_outstanding, [], stock_code=symbol)
    
    # 3. Run Cost Model v2 (Double Pool + Concentration)
    cost_v2 = CostSimulator(bin_size=bin_size, model_type="double_pool_dynamic")
    v2_history = cost_v2.run_daily_simulation(df_prices, shares_outstanding, [], shareholder_concentration=shareholder_concentration, stock_code=symbol)
    
    # Signals containers
    vp_signals = []
    v1_signals = []
    v2_signals = []
    
    # Keep track of co-touch events on day t for McNemar's test
    co_touch_records = [] # elements: (date, vp_success, v1_success, v2_success)
    
    N = len(df_prices)
    for idx in range(warmup_days, N - 20):
        current_row = df_prices.iloc[idx]
        prev_close = df_prices.iloc[idx - 1]["Close"]
        low, high = current_row["Low"], current_row["High"]
        date_t = current_row["Date"]
        
        # Check touches
        vp_peaks = find_peaks(vp_history[idx - 1], bin_size, top_n=3)
        v1_peaks = find_peaks(v1_history[idx - 1]["Distribution"], bin_size, top_n=3)
        v2_peaks = find_peaks(v2_history[idx - 1]["Distribution"], bin_size, top_n=3)
        
        vp_touch = any(prev_close >= p and low <= p <= high for p in vp_peaks)
        v1_touch = any(prev_close >= p and low <= p <= high for p in v1_peaks)
        v2_touch = any(prev_close >= p and low <= p <= high for p in v2_peaks)
        
        # Helper to compute trading metrics for a touched peak
        def get_trade_metrics(peak):
            # Trading strategy: buy at t+1 Open
            entry_price = df_prices.iloc[idx+1]["Open"]
            stop_price = entry_price * 0.97
            target_price = entry_price * 1.08
            
            daily_returns = []
            trade_dates = []
            exit_date = df_prices.iloc[idx+5]["Date"]
            
            p_prev = entry_price
            stopped = False
            for k in range(1, 6):
                row_k = df_prices.iloc[idx + k]
                low_k, high_k, close_k = row_k["Low"], row_k["High"], row_k["Close"]
                date_k = row_k["Date"]
                
                # Check stop-loss
                if low_k <= stop_price:
                    daily_returns.append((stop_price - p_prev) / p_prev)
                    trade_dates.append(date_k)
                    exit_date = date_k
                    stopped = True
                    break
                # Check take-profit
                elif high_k >= target_price:
                    daily_returns.append((target_price - p_prev) / p_prev)
                    trade_dates.append(date_k)
                    exit_date = date_k
                    stopped = True
                    break
                else:
                    daily_returns.append((close_k - p_prev) / p_prev)
                    trade_dates.append(date_k)
                    p_prev = close_k
                    
            # 5-day bounce defined as: max close price in next 5 days goes up >= 2% from peak
            closes_5d = df_prices.iloc[idx:idx+5]["Close"].values
            lows_5d = df_prices.iloc[idx:idx+5]["Low"].values
            highs_5d = df_prices.iloc[idx:idx+5]["High"].values
            
            success = int(len(closes_5d) > 0 and max(closes_5d) >= peak * 1.02)
            ret_5d = (df_prices.iloc[idx+5]["Close"] - peak) / peak
            ret_20d = (df_prices.iloc[idx+20]["Close"] - peak) / peak
            mae = min((lows_5d - peak) / peak) if len(lows_5d) > 0 else 0.0
            mfe = max((highs_5d - peak) / peak) if len(highs_5d) > 0 else 0.0
            
            return {
                "entry_date": df_prices.iloc[idx+1]["Date"],
                "exit_date": exit_date,
                "daily_returns": daily_returns,
                "trade_dates": trade_dates,
                "success": success,
                "ret_5d": ret_5d,
                "ret_20d": ret_20d,
                "mae": mae,
                "mfe": mfe
            }
            
        vp_meta = None
        v1_meta = None
        v2_meta = None
        
        if vp_touch:
            peak = next(p for p in vp_peaks if prev_close >= p and low <= p <= high)
            vp_meta = get_trade_metrics(peak)
            vp_signals.append(vp_meta)
        if v1_touch:
            peak = next(p for p in v1_peaks if prev_close >= p and low <= p <= high)
            v1_meta = get_trade_metrics(peak)
            v1_signals.append(v1_meta)
        if v2_touch:
            peak = next(p for p in v2_peaks if prev_close >= p and low <= p <= high)
            v2_meta = get_trade_metrics(peak)
            v2_signals.append(v2_meta)
            
        # Co-touch recording (all three models triggered touch on day t)
        if vp_touch and v1_touch and v2_touch:
            co_touch_records.append((date_t, vp_meta["success"], v1_meta["success"], v2_meta["success"]))
            
    return {
        "symbol": symbol,
        "prices": df_prices,
        "vp": vp_signals,
        "v1": v1_signals,
        "v2": v2_signals,
        "co_touches": co_touch_records
    }

def print_quant_ab_test_report(results_list: list):
    print("\n" + "="*95)
    print("【量化持股成本模型三方 A/B 測試與統計顯著性驗證報告】")
    print("="*95)
    
    total_vp_touches = 0
    total_vp_bounces = 0
    total_v1_touches = 0
    total_v1_bounces = 0
    total_v2_touches = 0
    total_v2_bounces = 0
    
    vp_ret_5 = []
    vp_ret_20 = []
    vp_mae = []
    vp_mfe = []
    
    v1_ret_5 = []
    v1_ret_20 = []
    v1_mae = []
    v1_mfe = []
    
    v2_ret_5 = []
    v2_ret_20 = []
    v2_mae = []
    v2_mfe = []
    
    # For Wilcoxon signed-rank test on stock-level 5-day bounce rates
    wilcoxon_stocks = []
    vp_bounce_rates = []
    v1_bounce_rates = []
    v2_bounce_rates = []
    
    # Co-touches container for McNemar
    all_vp_co_success = []
    all_v1_co_success = []
    all_v2_co_success = []
    
    all_vp_signals = []
    all_v1_signals = []
    all_v2_signals = []
    
    for r in results_list:
        if r is None:
            continue
        symbol = r["symbol"]
        
        vp_t = len(r["vp"])
        v1_t = len(r["v1"])
        v2_t = len(r["v2"])
        
        if vp_t > 0 and v1_t > 0 and v2_t > 0:
            wilcoxon_stocks.append(symbol)
            vp_bounce_rates.append(sum(s["success"] for s in r["vp"]) / vp_t)
            v1_bounce_rates.append(sum(s["success"] for s in r["v1"]) / v1_t)
            v2_bounce_rates.append(sum(s["success"] for s in r["v2"]) / v2_t)
            
        total_vp_touches += vp_t
        total_vp_bounces += sum(s["success"] for s in r["vp"])
        vp_ret_5.extend([s["ret_5d"] for s in r["vp"]])
        vp_ret_20.extend([s["ret_20d"] for s in r["vp"]])
        vp_mae.extend([s["mae"] for s in r["vp"]])
        vp_mfe.extend([s["mfe"] for s in r["vp"]])
        all_vp_signals.extend(r["vp"])
        
        total_v1_touches += v1_t
        total_v1_bounces += sum(s["success"] for s in r["v1"])
        v1_ret_5.extend([s["ret_5d"] for s in r["v1"]])
        v1_ret_20.extend([s["ret_20d"] for s in r["v1"]])
        v1_mae.extend([s["mae"] for s in r["v1"]])
        v1_mfe.extend([s["mfe"] for s in r["v1"]])
        all_v1_signals.extend(r["v1"])
        
        total_v2_touches += v2_t
        total_v2_bounces += sum(s["success"] for s in r["v2"])
        v2_ret_5.extend([s["ret_5d"] for s in r["v2"]])
        v2_ret_20.extend([s["ret_20d"] for s in r["v2"]])
        v2_mae.extend([s["mae"] for s in r["v2"]])
        v2_mfe.extend([s["mfe"] for s in r["v2"]])
        all_v2_signals.extend(r["v2"])
        
        # Co-touches for McNemar
        for ct in r["co_touches"]:
            all_vp_co_success.append(ct[1])
            all_v1_co_success.append(ct[2])
            all_v2_co_success.append(ct[3])
            
    # Portfolio curves
    vp_port = calculate_portfolio_metrics(all_vp_signals)
    v1_port = calculate_portfolio_metrics(all_v1_signals)
    v2_port = calculate_portfolio_metrics(all_v2_signals)
    
    # Output Table 1: Signal & Return Metrics
    print(f"{'模型特徵':<32} | {'總觸碰數':<8} | {'5日反彈率':<9} | {'5日均回報':<9} | {'20日均回報':<10} | {'5日均 MAE':<9} | {'5日均 MFE':<9}")
    print("-"*105)
    print(f"{'1. Volume Profile (Baseline)':<32} | {total_vp_touches:<8} | {(total_vp_bounces/total_vp_touches*100):.2f}% | {np.mean(vp_ret_5)*100:+.2f}%   | {np.mean(vp_ret_20)*100:+.2f}%    | {np.mean(vp_mae)*100:.2f}%   | {np.mean(vp_mfe)*100:.2f}%")
    print(f"{'2. Cost Model v1 (Single Pool)':<32} | {total_v1_touches:<8} | {(total_v1_bounces/total_v1_touches*100):.2f}% | {np.mean(v1_ret_5)*100:+.2f}%   | {np.mean(v1_ret_20)*100:+.2f}%    | {np.mean(v1_mae)*100:.2f}%   | {np.mean(v1_mfe)*100:.2f}%")
    print(f"{'3. Cost Model v2 (Double+Concentr)':<32} | {total_v2_touches:<8} | {(total_v2_bounces/total_v2_touches*100):.2f}% | {np.mean(v2_ret_5)*100:+.2f}%   | {np.mean(v2_ret_20)*100:+.2f}%    | {np.mean(v2_mae)*100:.2f}%   | {np.mean(v2_mfe)*100:.2f}%")
    print("="*105)
    
    # Output Table 2: Trading Strategy Metrics (Sharpe, MDD)
    print("\n" + "="*95)
    print("【交易策略模擬績效對比 (-3% 止損 / +8% 止盈)】")
    print("="*95)
    print(f"{'模型':<30} | {'年化收益':<8} | {'年化波動':<8} | {'夏普值 Sharpe':<13} | {'索提諾 Sortino':<14} | {'最大回撤 MDD':<12} | {'獲利因子 PF':<11}")
    print("-"*95)
    print(f"{'1. Volume Profile (Baseline)':<30} | {vp_port['return']*100:+.2f}%   | {vp_port['vol']*100:.2f}%   | {vp_port['sharpe']:.2f}         | {vp_port['sortino']:.2f}          | {vp_port['mdd']*100:.2f}%       | {vp_port['pf']:.2f}")
    print(f"{'2. Cost Model v1 (Single Pool)':<30} | {v1_port['return']*100:+.2f}%   | {v1_port['vol']*100:.2f}%   | {v1_port['sharpe']:.2f}         | {v1_port['sortino']:.2f}          | {v1_port['mdd']*100:.2f}%       | {v1_port['pf']:.2f}")
    print(f"{'3. Cost Model v2 (Double+Concentr)':<30} | {v2_port['return']*100:+.2f}%   | {v2_port['vol']*100:.2f}%   | {v2_port['sharpe']:.2f}         | {v2_port['sortino']:.2f}          | {v2_port['mdd']*100:.2f}%       | {v2_port['pf']:.2f}")
    print("="*95)
    
    # Statistical Tests
    print("\n" + "="*95)
    print("【統計顯著性檢定結果 (McNemar & Wilcoxon)】")
    print("="*95)
    
    # 1. McNemar Test on Co-Touches
    print(f"1. 共同觸發事件配對檢定 (McNemar's Test) - 共 {len(all_vp_co_success)} 個配對事件:")
    mc_v2_vs_vp = mcnemar_test(all_v2_co_success, all_vp_co_success)
    print(f"  * Cost Model v2 vs. Volume Profile Baseline:")
    print(f"    - Contingency Table: {mc_v2_vs_vp['contingency_table']}")
    print(f"    - Chi-Square: {mc_v2_vs_vp['chi2']:.4f}, p-value: {mc_v2_vs_vp['p_value']:.4e} (是否顯著: {mc_v2_vs_vp['significant']})")
    
    mc_v2_vs_v1 = mcnemar_test(all_v2_co_success, all_v1_co_success)
    print(f"  * Cost Model v2 vs. Cost Model v1 (Single Pool) [Ablation Study]:")
    print(f"    - Contingency Table: {mc_v2_vs_v1['contingency_table']}")
    print(f"    - Chi-Square: {mc_v2_vs_v1['chi2']:.4f}, p-value: {mc_v2_vs_v1['p_value']:.4e} (是否顯著: {mc_v2_vs_v1['significant']})")
    
    # 2. Wilcoxon Signed-Rank Test on Stock-level Bounce Rates
    print(f"\n2. 個股反彈勝率配對符號等級檢定 (Wilcoxon Signed-Rank Test) - 共 {len(wilcoxon_stocks)} 檔股票:")
    wx_v2_vs_vp = wilcoxon_test(v2_bounce_rates, vp_bounce_rates)
    print(f"  * Cost Model v2 vs. Volume Profile Baseline:")
    print(f"    - W-Statistic: {wx_v2_vs_vp['w_statistic']:.1f}, Z-Statistic: {wx_v2_vs_vp['z_statistic']:.4f}, p-value: {wx_v2_vs_vp['p_value']:.4e} (是否顯著: {wx_v2_vs_vp['significant']})")
    
    wx_v2_vs_v1 = wilcoxon_test(v2_bounce_rates, v1_bounce_rates)
    print(f"  * Cost Model v2 vs. Cost Model v1 (Single Pool) [Ablation Study]:")
    print(f"    - W-Statistic: {wx_v2_vs_v1['w_statistic']:.1f}, Z-Statistic: {wx_v2_vs_v1['z_statistic']:.4f}, p-value: {wx_v2_vs_v1['p_value']:.4e} (是否顯著: {wx_v2_vs_v1['significant']})")
    print("="*95 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, default="all", help="Comma separated stock symbols or 'all'")
    args = parser.parse_args()
    
    if args.symbols.strip().lower() == "all":
        # Find all 130 common stocks that have both daily price and shareholder concentration files
        loader = DataLoader()
        prices_csv = loader.yahoo_dir / "raw_yahoo_finance_daily_price.csv"
        conc_csv = loader.goodinfo_dir / "raw_equity_class_his.csv"
        
        df_p = pd.read_csv(prices_csv, usecols=["stock_code"], dtype=str)
        df_c = pd.read_csv(conc_csv, usecols=["stock_code"], dtype=str)
        common_symbols = sorted(list(set(df_p["stock_code"].dropna()) & set(df_c["stock_code"].dropna())))
        print(f"Loaded {len(common_symbols)} common stocks for A/B testing backtest.")
        symbols_list = common_symbols
    else:
        symbols_list = [s.strip() for s in args.symbols.split(",") if s.strip()]
        
    results = []
    for idx, sym in enumerate(symbols_list):
        print(f"[{idx+1}/{len(symbols_list)}] Simulating {sym}...")
        res = backtest_single_stock(sym)
        if res is not None:
            results.append(res)
            
    print_quant_ab_test_report(results)
