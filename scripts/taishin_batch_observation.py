import os
import sys
import time
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

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

REPO_ROOT = Path(__file__).resolve().parent.parent


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
    print("=" * 80)
    print("【台新證券 Nova API 觀察名單 (StockID_TWSE_TPEX.csv) 小時 K 線批量下載與成本模擬器】")
    print("=" * 80)

    creds = load_taishin_credentials()
    obs_csv = REPO_ROOT / "StockID_TWSE_TPEX.csv"
    if not obs_csv.exists():
        print(f"[Error] Observation CSV list not found at {obs_csv}")
        sys.exit(1)

    df_obs = pd.read_csv(obs_csv, dtype={"代號": str})
    print(f"Loaded {len(df_obs)} entries from observation list (含 0000 加權指數，改用 IX0001 下載).")

    cert_path = str(Path("C:/Users/WJLEE/SynologyDrive/NAS/github.com/GoogleSheet.Banks") / creds["cert_rel_path"])

    print(f"\n[1/4] 正在登入台新證券 Nova API...")
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

    # Four chunks covering ~3 years of hourly data (earliest available is 2023-05-23),
    # each strictly < 365 days to satisfy the API limit.
    today_str = datetime.now().strftime("%Y-%m-%d")
    chunks = [
        ("2023-05-23", "2024-03-31"),
        ("2024-04-01", "2025-01-31"),
        ("2025-02-01", "2025-11-30"),
        ("2025-12-01", today_str)
    ]

    loader = DataLoader()
    output_dir = REPO_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    failed = []

    print(f"\n[2/4] 開始進行 {len(df_obs)} 檔股票之 3 年小時 K 線分段下載與快取...")
    for idx, row in df_obs.iterrows():
        symbol = str(row["代號"]).strip()
        name_csv = str(row["名稱"]).strip()
        is_index = (symbol == "0000")
        # TAIEX: the API rejects "0000"; the index symbol is IX0001 and its
        # candle volume field is trade VALUE (NTD), not share count.
        api_symbol = "IX0001" if is_index else symbol
        company_name = "台灣加權指數" if is_index else get_company_name(loader.data_dir, symbol)
        if company_name == "個股":
            company_name = name_csv

        print(f"\n[{idx+1}/{len(df_obs)}] 處理 {company_name} ({symbol})")

        intraday_data_dir = REPO_ROOT / "data" / "Taishin.Intraday"
        intraday_data_dir.mkdir(parents=True, exist_ok=True)
        csv_data_path = intraday_data_dir / f"{symbol}_intraday_60m.csv"

        df_hourly = None
        # Reuse cached 3-year hourly K-line data if present (>10KB means a full download)
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
                        "symbol": api_symbol,
                        "timeframe": "60",
                        "from": start_date,
                        "to": end_date
                    })
                    if res and "data" in res and res["data"]:
                        all_candles.extend(res["data"])
                    time.sleep(1.0)
                except Exception as e:
                    print(f"    [Error] 下載分段失敗: {e}")
                    time.sleep(2.0)

            if not all_candles:
                print(f"  [Error] {symbol} 未取得任何 K 線資料，略過。")
                failed.append({"Symbol": symbol, "Name": company_name, "Reason": "無K線資料"})
                continue

            unique_candles = {}
            for c in all_candles:
                unique_candles[c["date"]] = c
            sorted_candles = [unique_candles[k] for k in sorted(unique_candles.keys())]
            print(f"  * 合併完成，共 {len(sorted_candles)} 筆無重複小時 K 線記錄")

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
            if not is_index:
                # Stocks: convert lots (張) to shares; index volume is already trade value in NTD
                df_hourly["Volume"] = df_hourly["Volume"] * 1000
            df_hourly = df_hourly.sort_values("Date").reset_index(drop=True)

            df_hourly.to_csv(csv_data_path, index=False)

        # Load parameters
        if is_index:
            # Index has no share capital. Volume is trade value (NTD), so use total
            # market cap (~75T NTD) as the divisor: turnover = value / market cap.
            # free_float_ratio default is 0.90, so scale up to land on ~75e12.
            shares_outstanding = 75e12 / 0.90
            corporate_actions = []
            shareholder_concentration = pd.DataFrame()
        else:
            shares_outstanding = loader.load_shares_outstanding(symbol)
            corporate_actions = loader.load_corporate_actions(symbol)
            shareholder_concentration = loader.load_weekly_shareholder_concentration(symbol)

        # Daily prices for the pre-hourly warming period (max 10 years back)
        df_daily_pre = pd.DataFrame()
        df_daily = pd.DataFrame()
        try:
            if is_index:
                raise ValueError("指數無日 K 暖機資料 (Yahoo CSV 不含 0000)")
            df_daily = loader.load_daily_prices(symbol)
            df_daily["Date_Naive"] = pd.to_datetime(df_daily["Date"]).dt.tz_localize(None)
            hourly_start_day = pd.to_datetime(df_hourly.iloc[0]["Date"]).normalize().tz_localize(None)
            ten_years_ago = hourly_start_day - pd.DateOffset(years=10)
            df_daily_pre = df_daily[(df_daily["Date_Naive"] >= ten_years_ago) & (df_daily["Date_Naive"] < hourly_start_day)].copy()
            df_daily_pre = df_daily_pre.drop(columns=["Date_Naive"])

            if not df_daily_pre.empty:
                print(f"  * 載入 {len(df_daily_pre)} 筆日 K 線進行前期籌碼暖機 (從 {df_daily_pre['Date'].min().strftime('%Y/%m/%d')} 至 {df_daily_pre['Date'].max().strftime('%Y/%m/%d')})...")
        except Exception as e:
            print(f"  [Warning] 無法載入日 K 線進行暖機: {e}")

        # Bin size from the first hourly close
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

        print(f"  [3/4] 執行混和籌碼成本模擬 (Bin Size: {bin_size})...")
        try:
            simulator = CostSimulator(bin_size=bin_size, model_type="double_pool_dynamic")

            # Step A: Warm up with daily data (prices in the CSV are already back-adjusted)
            daily_history = []
            if not df_daily_pre.empty:
                daily_history = simulator.run_daily_simulation(
                    df_prices=df_daily_pre,
                    shares_outstanding=shares_outstanding,
                    corporate_actions=[],
                    shareholder_concentration=shareholder_concentration,
                    stock_code=symbol
                )

            # Transition scaling: map adjusted daily bins onto the unadjusted hourly start price
            if not df_daily_pre.empty and not df_hourly.empty:
                daily_end_price = df_daily_pre.iloc[-1]["Close"]
                hourly_start_price = df_hourly.iloc[0]["Close"]
                if daily_end_price > 0:
                    scale_factor = hourly_start_price / daily_end_price
                    simulator.active_dist = {simulator.get_bin(p * scale_factor): w for p, w in simulator.active_dist.items()}
                    simulator.core_dist = {simulator.get_bin(p * scale_factor): w for p, w in simulator.core_dist.items()}
                    simulator.update_main_distribution()

            # Step B: Continue with hourly data (unadjusted, corporate actions applied dynamically)
            hourly_history = simulator.run_hourly_simulation(
                df_hourly=df_hourly,
                shares_outstanding=shares_outstanding,
                corporate_actions=corporate_actions,
                shareholder_concentration=shareholder_concentration,
                stock_code=symbol
            )

            history_records = daily_history + hourly_history

            final_dist = simulator.distribution
            last_close = df_hourly.iloc[-1]["Close"]
            metrics = CostMetrics.calculate_all(final_dist, last_close)

            df_hist = pd.DataFrame(history_records)
            total_trading_days = len(df_daily) if not df_daily.empty else 0
            trust = CostMetrics.evaluate_trust(
                df_history=df_hist,
                total_trading_days=total_trading_days,
                stock_code=symbol,
                is_index=is_index,
                data_as_of=df_hourly.iloc[-1]["Date"]
            )
            trust_level = trust["label"]

            chart_path = output_dir / f"{symbol}_cost_distribution_taishin.png"
            CostVisualizer.plot_cost_chart(
                df_history=df_hist,
                final_dist=final_dist,
                metrics=metrics,
                stock_code=symbol,
                company_name=company_name,
                save_path=chart_path,
                shares_outstanding=shares_outstanding,
                trust_level=trust_level,
                data_as_of=trust["data_as_of"]
            )

            csv_dir = output_dir / "csv"
            csv_dir.mkdir(parents=True, exist_ok=True)
            csv_path = csv_dir / f"{symbol}_cost_distribution_taishin.csv"
            dist_data = [
                {
                    "price": k,
                    "weight": v,
                    "trust_level": trust_level,
                    "data_as_of": trust["data_as_of"],
                    "staleness_days": trust["staleness_days"]
                }
                for k, v in sorted(final_dist.items())
            ]
            df_dist = pd.DataFrame(dist_data)
            df_dist.to_csv(csv_path, index=False)

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
                "TrustLevel": trust_level,
                "DataAsOf": trust["data_as_of"]
            })
            print(f"  * 成功完成並繪製圖表！")

        except Exception as e:
            print(f"  [Error] 模擬或圖表生成失敗: {e}")
            failed.append({"Symbol": symbol, "Name": company_name, "Reason": str(e)})

    print(f"\n[4/4] 正在生成觀察名單台新高頻小時級評估總報告...")
    write_observation_report(results, failed)
    print("All batch processing completed successfully!")


def write_observation_report(results, failed):
    output_dir = REPO_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "taishin_observation_validation_report.md"

    table_lines = [
        "| 股票代號與名稱 | 最新收盤價 (元) | 平均成本 (元) | 中位成本 (元) | 最密集籌碼點 POC | 獲利籌碼佔比 | 套牢籌碼佔比 | 模型可信度 | 資料截至 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    image_lines = []

    for r in results:
        table_lines.append(
            f"| **{r['Symbol']} {r['Name']}** | {r['Close']:.2f} | {r['AvgCost']:.2f} | {r['MedianCost']:.2f} | {r['POC']:.2f} ({r['POC_Weight']:.1f}%) | {r['ProfitRatio']:.2f}% | {r['LossRatio']:.2f}% | **{r['TrustLevel']}** | {r.get('DataAsOf') or '-'} |"
        )
        image_lines.append(
            f"### {r['Symbol']} {r['Name']}\n\n![{r['Name']} {r['Symbol']} 籌碼成本分佈圖](./{r['Symbol']}_cost_distribution_taishin.png)"
        )

    failed_lines = []
    if failed:
        failed_lines.append("## 三、 處理失敗清單\n")
        failed_lines.append("| 股票代號 | 名稱 | 原因 |")
        failed_lines.append("| :--- | :--- | :--- |")
        for f in failed:
            failed_lines.append(f"| {f['Symbol']} | {f['Name']} | {f['Reason']} |")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    markdown_content = f"""# 觀察名單籌碼持股成本分佈評估報告 (台新 Nova API 高頻小時級)

本報告涵蓋觀察名單 StockID_TWSE_TPEX.csv（成功 {len(results)} 檔 / 失敗 {len(failed)} 檔）的市場持股成本分佈模擬結果與可信度評估。
採用 **台新證券 Nova API 小時級 K 線（60-Minute Candles）** 搭配最長 10 年日 K 暖機的混和模擬。

---

## 一、 觀察名單數據總覽

{chr(10).join(table_lines)}

---

## 二、 個股籌碼分佈圖

{chr(10).join(image_lines)}

{chr(10).join(failed_lines)}

報告生成時間：{generated_at}
"""

    report_path.write_text(markdown_content, encoding='utf-8')
    print(f"Observation report saved to: {report_path}")


if __name__ == "__main__":
    main()
