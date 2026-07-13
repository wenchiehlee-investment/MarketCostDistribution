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
    if n < 10:
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

def calculate_portfolio_metrics(trade_signals: list, friction_cost: float = 0.0) -> dict:
    """
    Constructs a daily portfolio equity curve and calculates standard quant metrics,
    including the actual annualized single-sided weight-based turnover.
    """
    if not trade_signals:
        return {"return": 0.0, "vol": 0.0, "sharpe": 0.0, "sortino": 0.0, "mdd": 0.0, "pf": 0.0, "turnover": 0.0}
        
    daily_active_trades = {}
    for idx, sig in enumerate(trade_signals):
        trade_id = idx
        rets = list(sig.get("daily_returns", []))
        dates = list(sig.get("trade_dates", []))
        if rets and friction_cost > 0.0:
            # Subtract friction cost from the final day's return of the trade
            rets[-1] -= friction_cost
            
        for d, ret in zip(dates, rets):
            if d not in daily_active_trades:
                daily_active_trades[d] = []
            daily_active_trades[d].append((trade_id, ret))
            
    if not daily_active_trades:
        return {"return": 0.0, "vol": 0.0, "sharpe": 0.0, "sortino": 0.0, "mdd": 0.0, "pf": 0.0, "turnover": 0.0}
        
    sorted_dates = sorted(daily_active_trades.keys())
    
    daily_weights = {}
    portfolio_daily_returns = []
    
    for d in sorted_dates:
        trades = daily_active_trades[d]
        N_t = len(trades)
        daily_weights[d] = {}
        if N_t > 0:
            w_t = 1.0 / N_t
            r_port = 0.0
            for trade_id, ret in trades:
                daily_weights[d][trade_id] = w_t
                r_port += w_t * ret
            portfolio_daily_returns.append(r_port)
        else:
            portfolio_daily_returns.append(0.0)
            
    portfolio_daily_returns = np.array(portfolio_daily_returns)
    
    # Calculate daily target weight changes (Turnover)
    daily_turnovers = []
    for idx, d in enumerate(sorted_dates):
        w_curr = daily_weights[d]
        w_prev = daily_weights[sorted_dates[idx-1]] if idx > 0 else {}
        
        all_ids = set(w_curr.keys()) | set(w_prev.keys())
        t_turn = 0.5 * sum(abs(w_curr.get(tid, 0.0) - w_prev.get(tid, 0.0)) for tid in all_ids)
        daily_turnovers.append(t_turn)
        
    total_years = len(sorted_dates) / 252.0 if len(sorted_dates) > 0 else 1.0
    annualized_turnover = sum(daily_turnovers) / total_years if total_years > 0 else 0.0
    
    # Calculate metrics
    mean_ret = np.mean(portfolio_daily_returns)
    std_ret = np.std(portfolio_daily_returns)
    
    ann_return = mean_ret * 252
    ann_vol = std_ret * math.sqrt(252)
    
    sharpe = (ann_return / ann_vol) if ann_vol > 0 else 0.0
    
    neg_rets = portfolio_daily_returns[portfolio_daily_returns < 0]
    downside_std = np.std(neg_rets) * math.sqrt(252) if len(neg_rets) > 0 else 0.0
    sortino = (ann_return / downside_std) if downside_std > 0 else 0.0
    
    equity = np.cumprod(1.0 + portfolio_daily_returns)
    peaks = np.maximum.accumulate(equity)
    drawdowns = (equity - peaks) / peaks
    mdd = np.min(drawdowns) if len(drawdowns) > 0 else 0.0
    
    gross_profits = np.sum(portfolio_daily_returns[portfolio_daily_returns > 0])
    gross_losses = np.sum(np.abs(portfolio_daily_returns[portfolio_daily_returns < 0]))
    pf = (gross_profits / gross_losses) if gross_losses > 0 else 1.0
    
    return {
        "return": ann_return,
        "vol": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "mdd": mdd,
        "pf": pf,
        "turnover": annualized_turnover
    }

def run_multiple_regression(X_df: pd.DataFrame, y: np.ndarray) -> dict:
    """Runs multiple linear regression y = X * beta using numpy OLS."""
    N = len(y)
    X = np.column_stack([np.ones(N), X_df.values])
    k = X.shape[1]
    
    beta, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
    
    y_pred = X @ beta
    resid = y - y_pred
    rss = np.sum(resid**2)
    df = N - k
    s2 = rss / df if df > 0 else 0.0
    
    try:
        xtx_inv = np.linalg.inv(X.T @ X)
        cov_matrix = s2 * xtx_inv
        se = np.sqrt(np.diag(cov_matrix))
    except Exception:
        se = np.zeros(k)
        
    t_stats = []
    p_values = []
    for i in range(k):
        if se[i] > 0:
            t = beta[i] / se[i]
            p = 1.0 - math.erf(abs(t) / math.sqrt(2.0))
        else:
            t = 0.0
            p = 1.0
        t_stats.append(t)
        p_values.append(p)
        
    feature_names = ["Intercept"] + list(X_df.columns)
    results = {}
    for name, b, s_err, t, p in zip(feature_names, beta, se, t_stats, p_values):
        stars = ""
        if p < 0.01: stars = "***"
        elif p < 0.05: stars = "**"
        elif p < 0.10: stars = "*"
        results[name] = {
            "coefficient": b,
            "std_error": s_err,
            "t_stat": t,
            "p_value": p,
            "sig": stars
        }
    return results

def compute_decision_tree_importance(X_df: pd.DataFrame, y: np.ndarray) -> dict:
    """Computes Gini / Variance reduction feature importances using a 1-depth split search."""
    features = list(X_df.columns)
    X = X_df.values
    N, k = X.shape
    global_mean = np.mean(y)
    global_sse = np.sum((y - global_mean)**2)
    
    best_feat = None
    best_thresh = None
    best_reduction = 0.0
    
    feat_max_reduction = {}
    for fi in range(k):
        feat_vals = X[:, fi]
        thresholds = np.percentile(feat_vals, range(10, 95, 10))
        max_red = 0.0
        best_t_for_feat = None
        for t in thresholds:
            left_mask = feat_vals <= t
            right_mask = ~left_mask
            if np.sum(left_mask) < 5 or np.sum(right_mask) < 5:
                continue
            y_l = y[left_mask]
            y_r = y[right_mask]
            sse_l = np.sum((y_l - np.mean(y_l))**2)
            sse_r = np.sum((y_r - np.mean(y_r))**2)
            red = global_sse - (sse_l + sse_r)
            if red > max_red:
                max_red = red
                best_t_for_feat = t
        feat_max_reduction[features[fi]] = max_red
        if max_red > best_reduction:
            best_reduction = max_red
            best_feat = features[fi]
            best_thresh = best_t_for_feat
            
    total_red = sum(feat_max_reduction.values())
    importances = {}
    for f in features:
        importances[f] = (feat_max_reduction[f] / total_red * 100.0) if total_red > 0 else 25.0
        
    return {
        "best_split_feature": best_feat,
        "best_split_threshold": best_thresh,
        "importances": importances
    }

def backtest_single_stock(symbol: str, warmup_days: int = 250) -> dict:
    loader = DataLoader()
    try:
        df_prices = loader.load_daily_prices(symbol)
        shares_outstanding = loader.load_shares_outstanding(symbol)
        shareholder_concentration = loader.load_weekly_shareholder_concentration(symbol)
    except Exception:
        return None
        
    if df_prices.empty or len(df_prices) < warmup_days + 30:
        return None
        
    bin_size = 1.0 if symbol in ["2330", "2454", "3034"] else 0.5
    
    df_prices["SMA_200"] = df_prices["Close"].rolling(200).mean()
    rolling_vol = df_prices["Volume"].rolling(20).sum()
    rolling_pv = (df_prices["Close"] * df_prices["Volume"]).rolling(20).sum()
    df_prices["Rolling_VWAP"] = np.where(rolling_vol > 0, rolling_pv / rolling_vol, df_prices["Close"])
    
    vp = VolumeProfile(bin_size=bin_size)
    vp_history = []
    for idx, row in df_prices.iterrows():
        h, l, c = row["High"], row["Low"], row["Close"]
        vwap = (h + l + c) / 3.0 if (pd.notna(h) and pd.notna(l) and h > 0) else c
        vp.add_volume(l, h, vwap, row["Volume"])
        vp_history.append(dict(vp.distribution))
        
    cost_v1 = CostSimulator(bin_size=bin_size, model_type="single_pool")
    v1_history = cost_v1.run_daily_simulation(df_prices, shares_outstanding, [], stock_code=symbol)
    
    cost_v2 = CostSimulator(bin_size=bin_size, model_type="double_pool_dynamic")
    v2_history = cost_v2.run_daily_simulation(df_prices, shares_outstanding, [], shareholder_concentration=shareholder_concentration, stock_code=symbol)
    
    vp_signals = []
    v1_signals = []
    v2_signals = []
    sma_signals = []
    vwap_signals = []
    
    co_touch_records = []
    N = len(df_prices)
    
    for idx in range(warmup_days, N - 20):
        current_row = df_prices.iloc[idx]
        prev_close = df_prices.iloc[idx - 1]["Close"]
        low, high = current_row["Low"], current_row["High"]
        date_t = current_row["Date"]
        
        vp_peaks = find_peaks(vp_history[idx - 1], bin_size, top_n=3)
        v1_peaks = find_peaks(v1_history[idx - 1]["Distribution"], bin_size, top_n=3)
        v2_peaks = find_peaks(v2_history[idx - 1]["Distribution"], bin_size, top_n=3)
        
        ma_val = df_prices.iloc[idx - 1]["SMA_200"]
        vwap_val = df_prices.iloc[idx - 1]["Rolling_VWAP"]
        
        vp_touch = any(prev_close >= p and low <= p <= high for p in vp_peaks)
        v1_touch = any(prev_close >= p and low <= p <= high for p in v1_peaks)
        v2_touch = any(prev_close >= p and low <= p <= high for p in v2_peaks)
        
        sma_touch = (pd.notna(ma_val) and prev_close >= ma_val and low <= ma_val <= high)
        vwap_touch = (pd.notna(vwap_val) and prev_close >= vwap_val and low <= vwap_val <= high)
        
        def get_trade_metrics(peak):
            entry_price = df_prices.iloc[idx+1]["Open"]
            if entry_price <= 0: return None
            stop_price = entry_price * 0.97
            target_price = entry_price * 1.08
            
            daily_returns = []
            trade_dates = []
            exit_date = df_prices.iloc[idx+5]["Date"]
            p_prev = entry_price
            
            is_ambiguous = 0
            stopped_out = False
            
            for k in range(1, 6):
                row_k = df_prices.iloc[idx + k]
                low_k, high_k, close_k = row_k["Low"], row_k["High"], row_k["Close"]
                date_k = row_k["Date"]
                
                stop_breached = (low_k <= stop_price)
                target_breached = (high_k >= peak * 1.02)
                if stop_breached and target_breached:
                    is_ambiguous = 1
                
                if stop_breached:
                    daily_returns.append((stop_price - p_prev) / p_prev)
                    trade_dates.append(date_k)
                    exit_date = date_k
                    stopped_out = True
                    break
                elif high_k >= target_price:
                    daily_returns.append((target_price - p_prev) / p_prev)
                    trade_dates.append(date_k)
                    exit_date = date_k
                    break
                else:
                    daily_returns.append((close_k - p_prev) / p_prev)
                    trade_dates.append(date_k)
                    p_prev = close_k
                    
            # First-passage success definition: reached peak*1.02 before hitting stop price
            success = 0
            for k in range(1, 6):
                row_k = df_prices.iloc[idx + k]
                low_k, high_k = row_k["Low"], row_k["High"]
                if low_k <= stop_price:
                    success = 0
                    break
                elif high_k >= peak * 1.02:
                    success = 1
                    break
                    
            lows_5d = df_prices.iloc[idx+1:idx+6]["Low"].values
            highs_5d = df_prices.iloc[idx+1:idx+6]["High"].values
            
            ret_5d = (df_prices.iloc[idx+5]["Close"] - entry_price) / entry_price
            ret_20d = (df_prices.iloc[idx+20]["Close"] - entry_price) / entry_price
            
            mae = min(0.0, min((lows_5d - entry_price) / entry_price)) if len(lows_5d) > 0 else 0.0
            mfe = max(0.0, max((highs_5d - entry_price) / entry_price)) if len(highs_5d) > 0 else 0.0
            
            return {
                "entry_date": df_prices.iloc[idx+1]["Date"],
                "exit_date": exit_date,
                "daily_returns": daily_returns,
                "trade_dates": trade_dates,
                "success": success,
                "ret_5d": ret_5d,
                "ret_20d": ret_20d,
                "mae": mae,
                "mfe": mfe,
                "is_ambiguous": is_ambiguous
            }
            
        vp_meta = None
        v1_meta = None
        v2_meta = None
        
        if vp_touch:
            peak = next(p for p in vp_peaks if prev_close >= p and low <= p <= high)
            vp_meta = get_trade_metrics(peak)
            if vp_meta: vp_signals.append(vp_meta)
        if v1_touch:
            peak = next(p for p in v1_peaks if prev_close >= p and low <= p <= high)
            v1_meta = get_trade_metrics(peak)
            if v1_meta: v1_signals.append(v1_meta)
        if v2_touch:
            peak = next(p for p in v2_peaks if prev_close >= p and low <= p <= high)
            v2_meta = get_trade_metrics(peak)
            if v2_meta: v2_signals.append(v2_meta)
        if sma_touch:
            sma_meta = get_trade_metrics(ma_val)
            if sma_meta: sma_signals.append(sma_meta)
        if vwap_touch:
            vwap_meta = get_trade_metrics(vwap_val)
            if vwap_meta: vwap_signals.append(vwap_meta)
            
        if vp_touch and v1_touch and v2_touch and vp_meta and v1_meta and v2_meta:
            co_touch_records.append((date_t, vp_meta["success"], v1_meta["success"], v2_meta["success"]))
            
    avg_price = df_prices["Close"].mean()
    mcap_bln = (shares_outstanding * avg_price / 1e9) if shares_outstanding > 0 else 1.0
    avg_turnover_pct = (df_prices["Volume"] / shares_outstanding * 100).mean() if shares_outstanding > 0 else 0.0
    volatility_pct = (df_prices["Close"].pct_change().std() * 100)
    avg_core_pct = (shareholder_concentration["Core_Fraction"].mean() * 100) if shareholder_concentration is not None and not shareholder_concentration.empty else 60.0
    
    train_limit = pd.Timestamp("2022-12-31")
    
    vp_train = [s for s in vp_signals if s["entry_date"] <= train_limit]
    vp_test = [s for s in vp_signals if s["entry_date"] > train_limit]
    
    v1_train = [s for s in v1_signals if s["entry_date"] <= train_limit]
    v1_test = [s for s in v1_signals if s["entry_date"] > train_limit]
    
    v2_train = [s for s in v2_signals if s["entry_date"] <= train_limit]
    v2_test = [s for s in v2_signals if s["entry_date"] > train_limit]
    
    sma_train = [s for s in sma_signals if s["entry_date"] <= train_limit]
    sma_test = [s for s in sma_signals if s["entry_date"] > train_limit]
    
    vwap_train = [s for s in vwap_signals if s["entry_date"] <= train_limit]
    vwap_test = [s for s in vwap_signals if s["entry_date"] > train_limit]
    
    co_train = [ct for ct in co_touch_records if ct[0] <= train_limit]
    co_test = [ct for ct in co_touch_records if ct[0] > train_limit]
    
    return {
        "symbol": symbol,
        "prices": df_prices,
        "vp_train": vp_train,
        "v1_train": v1_train,
        "v2_train": v2_train,
        "sma200_train": sma_train,
        "vwap20_train": vwap_train,
        "co_touches_train": co_train,
        "vp_test": vp_test,
        "v1_test": v1_test,
        "v2_test": v2_test,
        "sma200_test": sma_test,
        "vwap20_test": vwap_test,
        "co_touches_test": co_test,
        "vp": vp_signals,
        "v1": v1_signals,
        "v2": v2_signals,
        "sma200": sma_signals,
        "vwap20": vwap_signals,
        "co_touches": co_touch_records,
        "features": {
            "Market_Cap_Bln": mcap_bln,
            "Turnover_Pct": avg_turnover_pct,
            "Volatility_Pct": volatility_pct,
            "Core_Fraction_Pct": avg_core_pct
        }
    }

def print_quant_ab_test_report(results_list: list):
    print("\n" + "="*115)
    print("【量化持股成本模型五方 A/B 測試與多基準模型驗證報告】")
    print("="*115)
    
    model_keys = ["vp", "sma200", "vwap20", "v1", "v2"]
    model_names = {
        "vp": "1. Volume Profile (Baseline)",
        "sma200": "2. SMA 200 (Baseline)",
        "vwap20": "3. Rolling VWAP 20d (Baseline)",
        "v1": "4. Cost Model v1 (Single Pool)",
        "v2": "5. Cost Model v2 (Double Pool Dynamic)"
    }
    
    touches = {k: 0 for k in model_keys}
    bounces = {k: 0 for k in model_keys}
    ret_5d = {k: [] for k in model_keys}
    ret_20d = {k: [] for k in model_keys}
    mae = {k: [] for k in model_keys}
    mfe = {k: [] for k in model_keys}
    signals = {k: [] for k in model_keys}
    
    wilcoxon_stocks = []
    bounce_rates_by_stock = {k: [] for k in model_keys}
    
    all_vp_co_success = []
    all_v1_co_success = []
    all_v2_co_success = []
    
    train_app_data = []
    test_app_data = []
    
    # Event decomposition
    v1_only_signals = []
    v2_only_signals = []
    both_signals_v1 = []
    both_signals_v2 = []
    
    total_signals_count = 0
    ambiguous_signals_count = 0
    
    for r in results_list:
        if r is None: continue
        sym = r["symbol"]
        
        has_all = all(len(r[k]) > 0 for k in model_keys)
        if has_all:
            wilcoxon_stocks.append(sym)
            for k in model_keys:
                bounce_rates_by_stock[k].append(sum(s["success"] for s in r[k]) / len(r[k]))
                
        # Signal decomposition
        v1_dates = {s["entry_date"]: s for s in r["v1"]}
        v2_dates = {s["entry_date"]: s for s in r["v2"]}
        both_dts = set(v1_dates.keys()) & set(v2_dates.keys())
        v1_only_dts = set(v1_dates.keys()) - set(v2_dates.keys())
        v2_only_dts = set(v2_dates.keys()) - set(v1_dates.keys())
        
        for d in both_dts:
            both_signals_v1.append(v1_dates[d])
            both_signals_v2.append(v2_dates[d])
        for d in v1_only_dts:
            v1_only_signals.append(v1_dates[d])
        for d in v2_only_dts:
            v2_only_signals.append(v2_dates[d])
            
        # Ambiguity ratio tracking
        for k in model_keys:
            for s in r[k]:
                total_signals_count += 1
                if s.get("is_ambiguous", 0) == 1:
                    ambiguous_signals_count += 1
                    
        # 1. Train applicability data (2016-2022)
        v1_tr_br = (sum(s["success"] for s in r["v1_train"]) / len(r["v1_train"])) if len(r["v1_train"]) > 0 else 0.0
        vp_tr_br = (sum(s["success"] for s in r["vp_train"]) / len(r["vp_train"])) if len(r["vp_train"]) > 0 else 0.0
        v2_tr_br = (sum(s["success"] for s in r["v2_train"]) / len(r["v2_train"])) if len(r["v2_train"]) > 0 else 0.0
        
        train_app_data.append({
            "Symbol": sym,
            "Market_Cap_Bln": r["features"]["Market_Cap_Bln"],
            "Log_Size": math.log(r["features"]["Market_Cap_Bln"]),
            "Turnover_Pct": r["features"]["Turnover_Pct"],
            "Volatility_Pct": r["features"]["Volatility_Pct"],
            "Core_Fraction_Pct": r["features"]["Core_Fraction_Pct"],
            "V1_Bounce": v1_tr_br,
            "V2_Bounce": v2_tr_br,
            "VP_Bounce": vp_tr_br,
            "V1_Premium": v1_tr_br - vp_tr_br,
            "V2_Premium": v2_tr_br - vp_tr_br,
            "V1_vs_V2_Premium": v1_tr_br - v2_tr_br
        })
        
        # 2. Test applicability data (2023-2026)
        v1_te_br = (sum(s["success"] for s in r["v1_test"]) / len(r["v1_test"])) if len(r["v1_test"]) > 0 else 0.0
        vp_te_br = (sum(s["success"] for s in r["vp_test"]) / len(r["vp_test"])) if len(r["vp_test"]) > 0 else 0.0
        v2_te_br = (sum(s["success"] for s in r["v2_test"]) / len(r["v2_test"])) if len(r["v2_test"]) > 0 else 0.0
        
        test_app_data.append({
            "Symbol": sym,
            "Market_Cap_Bln": r["features"]["Market_Cap_Bln"],
            "Log_Size": math.log(r["features"]["Market_Cap_Bln"]),
            "Turnover_Pct": r["features"]["Turnover_Pct"],
            "Volatility_Pct": r["features"]["Volatility_Pct"],
            "Core_Fraction_Pct": r["features"]["Core_Fraction_Pct"],
            "V1_Bounce": v1_te_br,
            "V2_Bounce": v2_te_br,
            "VP_Bounce": vp_te_br,
            "V1_Premium": v1_te_br - vp_te_br,
            "V2_Premium": v2_te_br - vp_te_br,
            "V1_vs_V2_Premium": v1_te_br - v2_te_br
        })
        
        for k in model_keys:
            touches[k] += len(r[k])
            bounces[k] += sum(s["success"] for s in r[k])
            ret_5d[k].extend([s["ret_5d"] for s in r[k]])
            ret_20d[k].extend([s["ret_20d"] for s in r[k]])
            mae[k].extend([s["mae"] for s in r[k]])
            mfe[k].extend([s["mfe"] for s in r[k]])
            signals[k].extend(r[k])
            
        for ct in r["co_touches"]:
            all_vp_co_success.append(ct[1])
            all_v1_co_success.append(ct[2])
            all_v2_co_success.append(ct[3])
            
    # Print Table 1
    print(f"{'模型特徵':<38} | {'總觸碰數':<8} | {'5日反彈率':<9} | {'5日均回報':<9} | {'20日均回報':<10} | {'5日均 MAE':<9} | {'5日均 MFE':<9}")
    print("-"*115)
    for k in model_keys:
        br = (bounces[k] / touches[k] * 100) if touches[k] > 0 else 0.0
        r5 = np.mean(ret_5d[k]) * 100 if ret_5d[k] else 0.0
        r20 = np.mean(ret_20d[k]) * 100 if ret_20d[k] else 0.0
        ae = np.mean(mae[k]) * 100 if mae[k] else 0.0
        fe = np.mean(mfe[k]) * 100 if mfe[k] else 0.0
        print(f"{model_names[k]:<38} | {touches[k]:<8} | {br:.2f}% | {r5:+.2f}%   | {r20:+.2f}%    | {ae:.2f}%   | {fe:.2f}%")
    print("="*115)
    
    # Print Table 2 with Friction Scenarios and Weight-based Turnover
    print("\n" + "="*115)
    print("【交易策略模擬績效與交易摩擦敏感度對比 (-3% 止損 / +8% 止盈)】")
    print("="*115)
    print(f"{'模型名稱':<35} | {'摩擦=0.0% (Sharpe/年化)':<22} | {'摩擦=0.414% (Sharpe/年化)':<22} | {'摩擦=0.60% (Sharpe/年化)':<22} | {'摩擦=0.90% (Sharpe/年化)':<22} | {'年化周轉率'}")
    print("-"*115)
    for k in model_keys:
        p_00 = calculate_portfolio_metrics(signals[k], friction_cost=0.0)
        p_04 = calculate_portfolio_metrics(signals[k], friction_cost=0.00414)
        p_06 = calculate_portfolio_metrics(signals[k], friction_cost=0.006)
        p_09 = calculate_portfolio_metrics(signals[k], friction_cost=0.009)
        print(f"{model_names[k]:<35} | {p_00['sharpe']:.2f} / {p_00['return']*100:+.2f}% | {p_04['sharpe']:.2f} / {p_04['return']*100:+.2f}% | {p_06['sharpe']:.2f} / {p_06['return']*100:+.2f}% | {p_09['sharpe']:.2f} / {p_09['return']*100:+.2f}% | {p_04['turnover']:.1f}x")
    print("="*115)
    
    # Print Table 3: V1 vs V2 Signal Partition Analysis
    print("\n" + "="*115)
    print("【Cost Model v1 vs. v2 信號集合拆解分析 (V1-only, V2-only, Common)】")
    print("="*115)
    print(f"{'事件分組':<25} | {'事件數 (N)':<10} | {'5日反彈率 (%)':<14} | {'5日均回報 (%)':<14} | {'5日均 MAE':<10} | {'5日均 MFE':<10} | {'摩擦0.414%回報'}")
    print("-"*115)
    
    partitions = {
        "V1-only Signals": v1_only_signals,
        "V2-only Signals": v2_only_signals,
        "Both (V1 Side)": both_signals_v1,
        "Both (V2 Side)": both_signals_v2
    }
    for name, sigs in partitions.items():
        cnt = len(sigs)
        if cnt > 0:
            br_p = sum(s["success"] for s in sigs) / cnt * 100
            r5_p = np.mean([s["ret_5d"] for s in sigs]) * 100
            mae_p = np.mean([s["mae"] for s in sigs]) * 100
            mfe_p = np.mean([s["mfe"] for s in sigs]) * 100
            net_p = r5_p - 0.414
        else:
            br_p = r5_p = mae_p = mfe_p = net_p = 0.0
        print(f"{name:<25} | {cnt:<10} | {br_p:.2f}%        | {r5_p:+.2f}%        | {mae_p:.2f}%    | {mfe_p:.2f}%    | {net_p:+.2f}%")
    print("="*115)
    
    # Print Ambiguity metrics
    ambiguity_ratio = (ambiguous_signals_count / total_signals_count * 100) if total_signals_count > 0 else 0.0
    print(f"\n* 交易路徑同日雙觸發 (Stop & Target同日觸及) 歧義事件數: {ambiguous_signals_count} / {total_signals_count} ({ambiguity_ratio:.2f}%)")
    
    # McNemar & Wilcoxon
    print("\n" + "="*115)
    print("【統計顯著性檢定結果 (McNemar & Wilcoxon)】")
    print("="*115)
    
    if len(all_vp_co_success) > 0:
        print(f"1. 共同觸發事件配對檢定 (McNemar's Test) - 共 {len(all_vp_co_success)} 個配對事件:")
        mc_v2_vs_vp = mcnemar_test(all_v2_co_success, all_vp_co_success)
        print(f"  * Cost Model v2 vs. Volume Profile Baseline: Chi-Square={mc_v2_vs_vp['chi2']:.4f}, p-value={mc_v2_vs_vp['p_value']:.4e} (是否顯著: {mc_v2_vs_vp['significant']})")
        print(f"    - 配對矩陣: a(共同成功)={mc_v2_vs_vp['contingency_table']['a']}, b(v2成功/VP失敗)={mc_v2_vs_vp['contingency_table']['b']}, c(v2失敗/VP成功)={mc_v2_vs_vp['contingency_table']['c']}, d(共同失敗)={mc_v2_vs_vp['contingency_table']['d']}")
        
        mc_v2_vs_v1 = mcnemar_test(all_v2_co_success, all_v1_co_success)
        print(f"  * Cost Model v2 vs. Cost Model v1 (Single Pool): Chi-Square={mc_v2_vs_v1['chi2']:.4f}, p-value={mc_v2_vs_v1['p_value']:.4e} (是否顯著: {mc_v2_vs_v1['significant']})")
        print(f"    - 配對矩陣: a(共同成功)={mc_v2_vs_v1['contingency_table']['a']}, b(v2成功/v1失敗)={mc_v2_vs_v1['contingency_table']['b']}, c(v2失敗/v1成功)={mc_v2_vs_v1['contingency_table']['c']}, d(共同失敗)={mc_v2_vs_v1['contingency_table']['d']}")
        
    if len(wilcoxon_stocks) >= 10:
        print(f"\n2. 個股反彈勝率配對符號等級檢定 (Wilcoxon Signed-Rank Test) - 共 {len(wilcoxon_stocks)} 檔股票:")
        wx_v2_vs_vp = wilcoxon_test(bounce_rates_by_stock["v2"], bounce_rates_by_stock["vp"])
        print(f"  * Cost Model v2 vs. Volume Profile Baseline: W={wx_v2_vs_vp['w_statistic']:.1f}, p-value={wx_v2_vs_vp['p_value']:.4e} (是否顯著: {wx_v2_vs_vp['significant']})")
        
        wx_v1_vs_v2 = wilcoxon_test(bounce_rates_by_stock["v1"], bounce_rates_by_stock["v2"])
        print(f"  * Cost Model v1 vs. Cost Model v2 [消融研究]: W={wx_v1_vs_v2['w_statistic']:.1f}, p-value={wx_v1_vs_v2['p_value']:.4e} (是否顯著: {wx_v1_vs_v2['significant']})")
    print("="*115)
    
    # 3. Cross-Sectional Applicability Analysis (Train Period 2016-2022)
    df_train_app = pd.DataFrame(train_app_data)
    df_test_app = pd.DataFrame(test_app_data)
    
    # OLS Regression on Train
    X_cols = ["Log_Size", "Turnover_Pct", "Volatility_Pct", "Core_Fraction_Pct"]
    y_train = df_train_app["V1_Premium"].values
    reg_results = run_multiple_regression(df_train_app[X_cols], y_train)
    
    # Decision Tree Feature Importance on Train
    dt_results = compute_decision_tree_importance(df_train_app[X_cols], y_train)
    
    print("\n" + "="*115)
    print("【模型適用性橫截面回歸分析 - 訓練期 (Cross-Sectional Regression 2016-2022)】")
    print("目標變數 (y) = 訓練期 Model v1 超額反彈率 (V1_Bounce_Rate - VP_Bounce_Rate)")
    print("="*115)
    print(f"{'自變數':<25} | {'係數 Beta':<12} | {'標準差 SE':<12} | {'t-Statistic':<12} | {'p-Value':<10} | {'顯著性'}")
    print("-"*115)
    for k, v in reg_results.items():
        print(f"{k:<25} | {v['coefficient']:+.6f} | {v['std_error']:.6f} | {v['t_stat']:+.4f} | {v['p_value']:.4e} | {v['sig']}")
    print("註：* p<0.10, ** p<0.05, *** p<0.01")
    print("="*115)
    
    print("\n" + "="*115)
    print("【決策樹適用性特徵重要性 - 訓練期 (Decision Tree Feature Importance 2016-2022)】")
    print("目標變數 (y) = 訓練期 Model v1 超額反彈率 (V1_Bounce_Rate - VP_Bounce_Rate)")
    print("="*115)
    print(f"根節點最佳分裂特徵 (Best Split Feature): {dt_results['best_split_feature']} (閾值 = {dt_results['best_split_threshold']:.4f})")
    print("-"*115)
    for f, imp in dt_results["importances"].items():
        print(f"{f:<25} | 重要性比重 (Importance Weight): {imp:.2f}%")
    print("="*115)
    
    # Out-of-sample temporal validation on Test Period (2023-2026) using optimal split threshold
    best_feat = dt_results["best_split_feature"]
    best_thresh = dt_results["best_split_threshold"]
    
    if best_feat is not None and best_thresh is not None:
        low_group = df_test_app[df_test_app[best_feat] <= best_thresh]
        high_group = df_test_app[df_test_app[best_feat] > best_thresh]
        
        print("\n" + "="*115)
        print(f"【適用性門檻樣本外時間驗證 (Out-of-Sample Temporal Validation 2023-2026)】")
        print(f"依據訓練期選出之門檻：{best_feat} = {best_thresh:.4f}")
        print("="*115)
        print(f"  * 樣本外低值組 (N={len(low_group)}): Model v1 勝率={low_group['V1_Bounce'].mean()*100:.2f}%, Baseline 勝率={low_group['VP_Bounce'].mean()*100:.2f}% (超額勝率={low_group['V1_Premium'].mean()*100:+.2f}%)")
        print(f"  * 樣本外高值組 (N={len(high_group)}): Model v1 勝率={high_group['V1_Bounce'].mean()*100:.2f}%, Baseline 勝率={high_group['VP_Bounce'].mean()*100:.2f}% (超額勝率={high_group['V1_Premium'].mean()*100:+.2f}%)")
        print("="*115 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, default="all", help="Comma separated stock symbols or 'all'")
    args = parser.parse_args()
    
    if args.symbols.strip().lower() == "all":
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
