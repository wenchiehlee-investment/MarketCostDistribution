import os
import sys
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
    """Reads the Taishin SDK credentials directly from the local GoogleSheet.Banks .env file."""
    env_path = Path("C:/Users/WJLEE/SynologyDrive/NAS/github.com/GoogleSheet.Banks/.env")
    if not env_path.exists():
        print(f"[Error] GoogleSheet.Banks .env file not found at: {env_path}")
        sys.exit(1)
        
    # Read variables
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
    print("【台新證券 Nova API 盤中高頻成本模擬器】")
    print("="*80)
    
    # 1. Load credentials
    creds = load_taishin_credentials()
    if not all([creds["personal_id"], creds["password"], creds["cert_pass"], creds["cert_rel_path"]]):
        print("[Error] Taishin credentials are not fully set in GoogleSheet.Banks/.env")
        sys.exit(1)
        
    cert_path = str(Path("C:/Users/WJLEE/SynologyDrive/NAS/github.com/GoogleSheet.Banks") / creds["cert_rel_path"])
    
    symbol = sys.argv[1] if len(sys.argv) > 1 else "2330"
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "60"
        
    # 2. Login to Taishin SDK
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
    
    # 3. Fetch candles based on timeframe
    print(f"\n[2/4] 正在拉取 {symbol} 的高頻 {timeframe} 分鐘 K 線資料...")
    try:
        if timeframe == "60":
            # For hourly candles, we can request up to 359 days of history
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=350)).strftime("%Y-%m-%d")
            print(f"  * 查詢範圍: {start_date} 至 {end_date} (約一年歷史)")
            res = reststock.historical.candles(**{
                "symbol": symbol,
                "timeframe": "60",
                "from": start_date,
                "to": end_date
            })
        else:
            # For 1-minute candles, Taishin API only returns the last 5 days (no date range parameter)
            print("  * 查詢範圍: 最近 5 天的 1 分鐘 K 線")
            res = reststock.historical.candles(**{
                "symbol": symbol,
                "timeframe": timeframe
            })
    except Exception as e:
        print(f"[Error] 拉取行情失敗: {e}")
        sys.exit(1)
        
    if not res or "data" not in res or not res["data"]:
        print("[Error] 未取得任何 K 線資料，請確認代號是否正確。")
        sys.exit(1)
        
    candles_data = res["data"]
    print(f"  * 成功下載 {len(candles_data)} 筆高頻 K 線記錄！")
    
    # Convert to DataFrame
    df_hourly = pd.DataFrame(candles_data)
    # Rename columns to match simulator expectations
    # Fields: date, open, high, low, close, volume, average
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
    # Sort chronologically (ascending date)
    df_hourly = df_hourly.sort_values("Date").reset_index(drop=True)
    
    # Save downloaded high-frequency data to local CSV
    intraday_data_dir = Path(__file__).resolve().parent.parent / "data" / "Taishin.Intraday"
    intraday_data_dir.mkdir(parents=True, exist_ok=True)
    csv_data_path = intraday_data_dir / f"{symbol}_intraday_{timeframe}m.csv"
    df_hourly.to_csv(csv_data_path, index=False)
    print(f"  * 高頻資料已快取至本地 CSV: {csv_data_path.resolve()}")
    
    # 4. Load basic parameters
    loader = DataLoader()
    company_name = get_company_name(loader.data_dir, symbol)
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
        hourly_start_naive = pd.to_datetime(df_hourly.iloc[0]["Date"]).tz_localize(None)
        df_daily_pre = df_daily[df_daily["Date_Naive"] < hourly_start_naive].copy()
        df_daily_pre = df_daily_pre.drop(columns=["Date_Naive"])
        
        if not df_daily_pre.empty:
            print(f"  * 載入 {len(df_daily_pre)} 筆日 K 線進行前期籌碼暖機 (從 {df_daily_pre['Date'].min().strftime('%Y/%m/%d')} 至 {df_daily_pre['Date'].max().strftime('%Y/%m/%d')})...")
    except Exception as e:
        print(f"  [Warning] 無法載入日 K 線進行暖機: {e}")
        
    # Calculate suitable bin size based on price level
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
        
    print(f"\n[3/4] 載入基本面資料，發行股數: {shares_outstanding / 1e8:.2f} 億股")
    print(f"     價格區間間距 (Bin Size): {bin_size} 元")
    print(f"     啟動 CostSimulator 進行混和籌碼成本模擬 (Model v1 - Single Pool)...")
    
    # 5. Run Hybrid Simulation
    simulator = CostSimulator(bin_size=bin_size, model_type="single_pool")
    
    daily_history = []
    if not df_daily_pre.empty:
        daily_history = simulator.run_daily_simulation(
            df_prices=df_daily_pre,
            shares_outstanding=shares_outstanding,
            corporate_actions=corporate_actions,
            shareholder_concentration=shareholder_concentration,
            stock_code=symbol
        )
        
    hourly_history = simulator.run_hourly_simulation(
        df_hourly=df_hourly,
        shares_outstanding=shares_outstanding,
        corporate_actions=corporate_actions,
        shareholder_concentration=shareholder_concentration,
        stock_code=symbol
    )
    
    history_records = daily_history + hourly_history
    print("     模擬完成！")
    
    # Calculate metrics
    final_dist = simulator.distribution
    last_close = df_hourly.iloc[-1]["Close"]
    metrics = CostMetrics.calculate_all(final_dist, last_close)
    
    # 6. Output Stats
    print("\n" + "="*50)
    print(f"【台新 Nova API 高頻籌碼持股成本分佈指標報告】")
    print(f"股票名稱: {company_name} ({symbol})")
    print(f"資料週期: {df_hourly['Date'].min().strftime('%Y/%m/%d')} 至 {df_hourly['Date'].max().strftime('%Y/%m/%d')}")
    print(f"最新收盤價: {last_close:.2f} 元")
    print(f"平均持股成本: {metrics['Average_Cost']:.2f} 元")
    print(f"最密集籌碼點 (POC): {metrics['POC']:.2f} 元 (佔比 {metrics['POC_Weight']*100:.2f}%)")
    print(f"獲利籌碼佔比 (股價 > 成本): {metrics['Profit_Ratio']*100:.2f}%")
    print(f"套牢籌碼佔比 (股價 < 成本): {metrics['Loss_Ratio']*100:.2f}%")
    print("="*50 + "\n")
    
    # 7. Generate Plot and save
    print("[4/4] 正在生成高頻持股成本分佈圖表...")
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
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
    
    # Copy to artifact registry
    artifact_dir = Path("C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919")
    dest_path = artifact_dir / f"{symbol}_cost_distribution_taishin.png"
    import shutil
    shutil.copy(str(chart_path), str(dest_path))
    
    print(f"\n[完成] 高頻視覺化圖表已存檔至：")
    print(f"  * 專案目錄: {chart_path.resolve()}")
    print(f"  * 報告附件: {dest_path.resolve()}")
    print("="*80)

if __name__ == "__main__":
    main()
