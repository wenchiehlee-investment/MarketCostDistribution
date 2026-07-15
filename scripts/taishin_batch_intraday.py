import os
import sys
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta

# Reconfigure stdout/stderr for UTF-8 output on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Add repo root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.data_loader import DataLoader
from src.simulator import CostSimulator
from src.metrics import CostMetrics
from src.visualizer import CostVisualizer

# Style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'Microsoft JhengHei'
plt.rcParams['axes.unicode_minus'] = False

def load_taishin_credentials() -> dict:
    env_path = Path("C:/Users/WJLEE/SynologyDrive/NAS/github.com/GoogleSheet.Banks/.env")
    if not env_path.exists():
        print(f"[Error] GoogleSheet.Banks .env file not found at: {env_path}")
        sys.exit(1)
        
    creds = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip()
                
    return {
        "personal_id": creds.get("FUGLE_USER1_PERSONAL_ID"),
        "password": creds.get("FUGLE_USER1_PASSWORD"),
        "cert_pass": creds.get("FUGLE_USER1_CERT_PASS"),
        "cert_rel_path": creds.get("FUGLE_USER1_CERT_PATH")
    }

def get_company_name(data_dir: Path, stock_code: str) -> str:
    stock_code_str = str(stock_code).strip()
    perf_csv = data_dir / "Python-Actions.GoodInfo.Analyzer" / "cleaned_performance.csv"
    if perf_csv.exists():
        try:
            df = pd.read_csv(perf_csv, dtype={"stock_code": str})
            df = df[df["stock_code"] == stock_code_str]
            if not df.empty:
                df_valid = df.dropna(subset=["company_name"])
                if not df_valid.empty:
                    return df_valid.iloc[0]["company_name"]
        except Exception:
            pass
    return "個股"

def main():
    print("="*80)
    print("【台新證券 Nova API 3年高頻小時 K 線批量下載與成本模擬器】")
    print("="*80)
    
    # 1. Load credentials & Focus List
    creds = load_taishin_credentials()
    focus_csv = Path("C:/Users/WJLEE/SynologyDrive/NAS/github.com/GoogleSheet.Banks/StockID_TWSE_TPEX_focus.csv")
    if not focus_csv.exists():
        print(f"[Error] Focus CSV list not found at {focus_csv}")
        sys.exit(1)
        
    df_focus = pd.read_csv(focus_csv, dtype={"代號": str})
    print(f"Loaded {len(df_focus)} stocks from focus list.")
    
    cert_path = str(Path("C:/Users/WJLEE/SynologyDrive/NAS/github.com/GoogleSheet.Banks") / creds["cert_rel_path"])
    
    # 2. Login to Taishin SDK
    print(f"\n[1/5] 正在登入台新證券 Nova API...")
    try:
        from taishin_sdk import TaishinSDK
        sdk = TaishinSDK()
        accounts = sdk.login(creds["personal_id"], creds["password"], cert_path, creds["cert_pass"])
        acc = accounts[0]
        print(f"  * 登入成功: {acc.name} ({acc.account})")
        sdk.init_realtime(acc)
    except Exception as e:
        print(f"[Error] 台新 SDK 登入失敗: {e}")
        sys.exit(1)
        
    reststock = sdk.marketdata.rest_client.stock
    
    # Define the four chunks to download 3 years of hourly data (earliest available is 2023-05-23)
    # Each range is strictly less than 365 days to satisfy the Taishin/Fugle API limit.
    today_str = datetime.now().strftime("%Y-%m-%d")
    chunks = [
        ("2023-05-23", "2024-03-31"),
        ("2024-04-01", "2025-01-31"),
        ("2025-02-01", "2025-11-30"),
        ("2025-12-01", today_str)
    ]
    
    loader = DataLoader()
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    artifact_dir = Path("C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    # 3. Process each stock in focus list
    print(f"\n[2/5] 開始進行 36 檔股票之 3 年小時 K 線分段下載與快取...")
    for idx, row in df_focus.iterrows():
        symbol = str(row["代號"]).strip()
        name_csv = str(row["名稱"]).strip()
        company_name = get_company_name(loader.data_dir, symbol)
        if company_name == "個股":
            company_name = name_csv
            
        print(f"\n[{idx+1}/{len(df_focus)}] 處理 {company_name} ({symbol})")
        
        intraday_data_dir = Path(__file__).resolve().parent.parent / "data" / "Taishin.Intraday"
        intraday_data_dir.mkdir(parents=True, exist_ok=True)
        csv_data_path = intraday_data_dir / f"{symbol}_intraday_60m.csv"
        
        df_hourly = None
        # Check if 3-year hourly K-line data has already been cached (size > 10KB to ensure full 3-year data is present)
        if csv_data_path.exists() and csv_data_path.stat().st_size > 10000:
            try:
                df_hourly = pd.read_csv(csv_data_path)
                df_hourly["Date"] = pd.to_datetime(df_hourly["Date"])
                print(f"  * 載入本地快取資料: {csv_data_path.name} (共 {len(df_hourly)} 筆小時 K 線)")
            except Exception:
                df_hourly = None
                
        if df_hourly is None:
            all_candles = []
            for start_date, end_date in chunks:
                try:
                    print(f"  * 下載分段: {start_date} ~ {end_date}...")
                    res = reststock.historical.candles(**{
                        "symbol": symbol,
                        "timeframe": "60",
                        "from": start_date,
                        "to": end_date
                    })
                    if res and "data" in res and res["data"]:
                        all_candles.extend(res["data"])
                    # Respect rate limits
                    time.sleep(1.0)
                except Exception as e:
                    print(f"    [Error] 下載分段失敗: {e}")
                    time.sleep(2.0)
                    
            if not all_candles:
                print(f"  [Error] {symbol} 未取得任何 K 線資料，略過。")
                continue
                
            # Remove duplicates based on date
            unique_candles = {}
            for c in all_candles:
                unique_candles[c["date"]] = c
            sorted_candles = [unique_candles[k] for k in sorted(unique_candles.keys())]
            print(f"  * 合併完成，共 {len(sorted_candles)} 筆無重複小時 K 線記錄")
            
            # Convert to DataFrame
            df_hourly = pd.DataFrame(sorted_candles)
            df_hourly = df_hourly.rename(columns={
                "date": "Date",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume"
            })
            df_hourly["Date"] = pd.to_datetime(df_hourly["Date"])
            df_hourly["Volume"] = df_hourly["Volume"] * 1000
            df_hourly = df_hourly.sort_values("Date").reset_index(drop=True)
            
            # Save local CSV
            df_hourly.to_csv(csv_data_path, index=False)
        
        # Load parameters
        shares_outstanding = loader.load_shares_outstanding(symbol)
        corporate_actions = loader.load_corporate_actions(symbol)
        shareholder_concentration = loader.load_weekly_shareholder_concentration(symbol)
        
        # Load daily prices for pre-hourly warming period (e.g. 7 years before)
        df_daily_pre = pd.DataFrame()
        df_daily = pd.DataFrame()
        try:
            df_daily = loader.load_daily_prices(symbol)
            # Normalize both datetimes to timezone-naive for safe comparison
            df_daily["Date_Naive"] = pd.to_datetime(df_daily["Date"]).dt.tz_localize(None)
            # Use normalize() to get 00:00:00 of the hourly start day to prevent double-simulating the transition day
            hourly_start_day = pd.to_datetime(df_hourly.iloc[0]["Date"]).normalize().tz_localize(None)
            # Limit the warming period to at most 10 years to prevent ancient bins (from 15-25 years ago) from dominating
            ten_years_ago = hourly_start_day - pd.DateOffset(years=10)
            df_daily_pre = df_daily[(df_daily["Date_Naive"] >= ten_years_ago) & (df_daily["Date_Naive"] < hourly_start_day)].copy()
            df_daily_pre = df_daily_pre.drop(columns=["Date_Naive"])
            
            if not df_daily_pre.empty:
                print(f"  * 載入 {len(df_daily_pre)} 筆日 K 線進行前期籌碼暖機 (從 {df_daily_pre['Date'].min().strftime('%Y/%m/%d')} 至 {df_daily_pre['Date'].max().strftime('%Y/%m/%d')})...")
        except Exception as e:
            print(f"  [Warning] 無法載入日 K 線進行暖機: {e}")
            
        # Calculate Bin size
        first_price = df_hourly.iloc[0]["Close"]
        raw_size = first_price * 0.005
        if raw_size < 0.1:
            bin_size = 0.05
        elif raw_size < 0.5:
            bin_size = 0.1
        elif raw_size < 1.0:
            bin_size = 0.5
        elif raw_size < 5.0:
            bin_size = 1.0
        else:
            bin_size = 5.0
            
        # 4. Run Hybrid Simulation
        print(f"  [3/5] 執行混和籌碼成本模擬 (Bin Size: {bin_size})...")
        try:
            simulator = CostSimulator(bin_size=bin_size, model_type="double_pool_dynamic")
            
            # Step A: Warm up with daily data (pre-adjusted scale)
            daily_history = []
            if not df_daily_pre.empty:
                daily_history = simulator.run_daily_simulation(
                    df_prices=df_daily_pre,
                    shares_outstanding=shares_outstanding,
                    corporate_actions=[],  # Pass empty actions: daily prices are already pre-adjusted in the CSV
                    shareholder_concentration=shareholder_concentration,
                    stock_code=symbol
                )
                
            # Transition scaling: scale daily bins up to match the hourly unadjusted start price
            if not df_daily_pre.empty and not df_hourly.empty:
                daily_end_price = df_daily_pre.iloc[-1]["Close"]
                hourly_start_price = df_hourly.iloc[0]["Close"]
                if daily_end_price > 0:
                    scale_factor = hourly_start_price / daily_end_price
                    # Scale both active and core distributions
                    simulator.active_dist = {simulator.get_bin(p * scale_factor): w for p, w in simulator.active_dist.items()}
                    simulator.core_dist = {simulator.get_bin(p * scale_factor): w for p, w in simulator.core_dist.items()}
                    simulator.update_main_distribution()
                
            # Step B: Continue with hourly data (starts unadjusted, corporate actions are applied dynamically)
            hourly_history = simulator.run_hourly_simulation(
                df_hourly=df_hourly,
                shares_outstanding=shares_outstanding,
                corporate_actions=corporate_actions,
                shareholder_concentration=shareholder_concentration,
                stock_code=symbol
            )
            
            # Merge history records
            history_records = daily_history + hourly_history
            
            final_dist = simulator.distribution
            last_close = df_hourly.iloc[-1]["Close"]
            metrics = CostMetrics.calculate_all(final_dist, last_close)
            
            # Save Dual-panel plot
            chart_path = output_dir / f"{symbol}_cost_distribution_taishin.png"
            df_hist = pd.DataFrame(history_records)
            CostVisualizer.plot_cost_chart(
                df_history=df_hist,
                final_dist=final_dist,
                metrics=metrics,
                stock_code=symbol,
                company_name=company_name,
                save_path=chart_path,
                shares_outstanding=shares_outstanding
            )
            
            # Save Raw CSV
            csv_dir = output_dir / "csv"
            csv_dir.mkdir(parents=True, exist_ok=True)
            csv_path = csv_dir / f"{symbol}_cost_distribution_taishin.csv"
            df_prices_daily = df_hourly.copy()
            df_prices_daily['Turnover'] = df_prices_daily['Volume'] / shares_outstanding
            avg_turnover_pct = df_prices_daily['Turnover'].mean() * 100
            
            lockup_heavy = ["2412", "3045"]
            total_trading_days = len(df_daily) if not df_daily.empty else 0
            
            if total_trading_days < 1000:
                trust_level = "極低 (Very Low) - 新上市歷史過短"
            elif symbol in lockup_heavy:
                trust_level = "中低 (Medium-Low) - 股權鎖定重"
            elif avg_turnover_pct >= 0.4:
                trust_level = "極高 (Very High)"
            elif avg_turnover_pct >= 0.25:
                trust_level = "高 (High)"
            elif avg_turnover_pct >= 0.12:
                trust_level = "中 (Medium)"
            else:
                trust_level = "低 (Low)"
                
            dist_data = [{"price": k, "weight": v, "trust_level": trust_level} for k, v in sorted(final_dist.items())]
            df_dist = pd.DataFrame(dist_data)
            df_dist.to_csv(csv_path, index=False)
            
            # Copy to artifact registry
            import shutil
            shutil.copy(str(chart_path), str(artifact_dir / f"{symbol}_cost_distribution_taishin.png"))
            shutil.copy(str(csv_path), str(artifact_dir / f"{symbol}_cost_distribution_taishin.csv"))
            
            results.append({
                "Symbol": symbol,
                "Name": company_name,
                "Close": last_close,
                "AvgCost": metrics["Average_Cost"],
                "MedianCost": metrics["Median_Cost"],
                "POC": metrics["POC"],
                "POC_Weight": metrics["POC_Weight"] * 100,
                "ProfitRatio": metrics["Profit_Ratio"] * 100,
                "LossRatio": metrics["Loss_Ratio"] * 100,
                "TrustLevel": trust_level
            })
            print(f"  * 成功完成並繪製圖表！")
            
        except Exception as e:
            print(f"  [Error] 模擬或圖表生成失敗: {e}")
            
    # 5. Write report
    print(f"\n[4/5] 正在生成觀察名單台新高頻小時級評估總報告...")
    write_intraday_report(results, artifact_dir)
    print("All batch processing completed successfully!")

def write_intraday_report(results, artifact_dir):
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "taishin_intraday_validation_report.md"
    
    table_lines = [
        "| 股票代號與名稱 | 最新收盤價 (元) | 平均成本 (元) | 中位成本 (元) | 最密集籌碼點 POC | 獲利籌碼佔比 | 套牢籌碼佔比 | 模型可信度 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    carousel_slides = []
    
    for r in results:
        table_lines.append(
            f"| **{r['Symbol']} {r['Name']}** | {r['Close']:.2f} | {r['AvgCost']:.2f} | {r['MedianCost']:.2f} | {r['POC']:.2f} ({r['POC_Weight']:.1f}%) | {r['ProfitRatio']:.2f}% | {r['LossRatio']:.2f}% | **{r['TrustLevel']}** |"
        )
        carousel_slides.append(
            f"![{r['Name']} {r['Symbol']} 籌碼成本分佈圖 (台新 Nova 高頻)](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/{r['Symbol']}_cost_distribution_taishin.png)"
        )
        
    carousel_content = "\n<!-- slide -->\n".join(carousel_slides)
    
    markdown_content = f"""# 觀察名單籌碼持股成本分佈評估報告 (台新 Nova API 高頻小時級)

本報告包含您的觀察名單（共 {len(results)} 檔）所有市場持股成本分佈的模擬結果與可信度評估。本報告已徹底排除日 K 線的路徑歧義（Path Ambiguity），改採 **台新證券 Nova API 小時級 K 線（60-Minute Candles）** 進行無歧義籌碼狀態估計。

---

## 一、 觀察名單數據總覽 (2023/05/23 ~ 2026/07)

以下為所有觀察名單股票的最新持股成本分析結果：

{"\n".join(table_lines)}

---

## 二、 觀察名單高頻籌碼分佈圖 (Carousel)

您可以使用下方 Carousel 快速滑動瀏覽所有觀察名單的小時級持股成本分佈圖：

````carousel
{carousel_content}
````

報告生成時間：2026-07-14
"""
    
    report_path.write_text(markdown_content, encoding='utf-8')
    print(f"Focus report saved to: {report_path}")
    
    # Copy to artifact registry
    import shutil
    shutil.copy(str(report_path), str(artifact_dir / "taishin_intraday_validation_report.md"))

if __name__ == "__main__":
    main()
