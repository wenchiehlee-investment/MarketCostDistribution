import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

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

def get_fugle_client(api_key: str):
    """Initializes and returns the RestClient from fugle-marketdata."""
    try:
        from fugle_marketdata import RestClient
        return RestClient(api_key=api_key)
    except ImportError:
        print("[Error] Required package 'fugle-marketdata' not found.")
        print("Please install it by running: pip install fugle-marketdata")
        sys.exit(1)

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
    # 1. Retrieve API key
    api_key = os.environ.get("FUGLE_API_KEY")
    if not api_key:
        print("="*80)
        print("【玉山富果行情 API 盤中高頻成本模擬器】")
        print("="*80)
        api_key = input("請輸入您的 Fugle API Key: ").strip()
        if not api_key:
            print("[Error] 未提供 API Key，程式中止。")
            sys.exit(1)
            
    symbol = input("請輸入台股代號 (預設為 2330): ").strip()
    if not symbol:
        symbol = "2330"
        
    timeframe = input("請選擇 K 線時間級別 (60 或 1，預設為 60 分鐘 K 線): ").strip()
    if not timeframe:
        timeframe = "60"
        
    print(f"\n[1/4] 正在透過 Fugle API 讀取 {symbol} 最近 30 天的 {timeframe} 分鐘高頻資料...")
    
    # 2. Fetch candles from Fugle
    client = get_fugle_client(api_key)
    try:
        # Fetch candles
        # Note: Fugle returns last 30 days for minute candles
        res = client.stock.historical.candles(
            symbol=symbol,
            timeframe=timeframe
        )
    except Exception as e:
        print(f"[Error] Fugle API 連線或讀取失敗: {e}")
        sys.exit(1)
        
    if not res or "candles" not in res or not res["candles"]:
        print("[Error] 未取得任何 K 線資料，請確認代號是否正確或 API Key 有效。")
        sys.exit(1)
        
    candles_data = res["candles"]
    print(f"成功下載 {len(candles_data)} 筆高頻 K 線記錄！")
    
    # Convert to DataFrame
    df_hourly = pd.DataFrame(candles_data)
    # Rename columns to match simulator expectations
    # Fugle fields: date, open, high, low, close, volume, turnover, change
    df_hourly = df_hourly.rename(columns={
        "date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    })
    df_hourly["Date"] = pd.to_datetime(df_hourly["Date"])
    df_hourly = df_hourly.sort_values("Date").reset_index(drop=True)
    
    # 3. Load shares outstanding & actions
    loader = DataLoader()
    company_name = get_company_name(loader.data_dir, symbol)
    shares_outstanding = loader.load_shares_outstanding(symbol)
    corporate_actions = loader.load_corporate_actions(symbol)
    shareholder_concentration = loader.load_weekly_shareholder_concentration(symbol)
    
    # Set suitable bin size
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
        
    print(f"[2/4] 載入公司基本面資料，發行股數: {shares_outstanding / 1e8:.2f} 億股")
    print(f"[3/4] 啟動 CostSimulator 進行高頻遞迴成本模擬 (Model v1 - Single Pool)...")
    
    # 4. Run Intraday Simulation
    simulator = CostSimulator(bin_size=bin_size, model_type="single_pool")
    history_records = simulator.run_hourly_simulation(
        df_hourly=df_hourly,
        shares_outstanding=shares_outstanding,
        corporate_actions=corporate_actions,
        shareholder_concentration=shareholder_concentration,
        stock_code=symbol
    )
    print("高頻成本模擬完成！")
    
    # Calculate metrics
    final_dist = simulator.distribution
    last_close = df_hourly.iloc[-1]["Close"]
    metrics = CostMetrics.calculate_all(final_dist, last_close)
    
    # 5. Output Stats
    print("\n" + "="*50)
    print(f"【Fugle 高頻籌碼持股成本分佈指標報告】")
    print(f"股票名稱: {company_name} ({symbol})")
    print(f"資料週期: 最近 30 天 {timeframe} 分鐘 K 線")
    print(f"最新收盤價: {last_close:.2f} 元")
    print(f"平均持股成本: {metrics['Average_Cost']:.2f} 元")
    print(f"最密集籌碼點 (POC): {metrics['POC']:.2f} 元 (佔比 {metrics['POC_Weight']*100:.2f}%)")
    print(f"獲利籌碼佔比 (股價 > 成本): {metrics['Profit_Ratio']*100:.2f}%")
    print(f"套牢籌碼佔比 (股價 < 成本): {metrics['Loss_Ratio']*100:.2f}%")
    print("="*50 + "\n")
    
    # 6. Generate Plot and save
    print("[4/4] 正在生成高頻持股成本分佈圖表...")
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / f"{symbol}_cost_distribution_intraday.png"
    
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
    dest_path = artifact_dir / f"{symbol}_cost_distribution_intraday.png"
    import shutil
    shutil.copy(str(chart_path), str(dest_path))
    
    print(f"\n[完成] 高頻視覺化圖表已存檔至：")
    print(f"  * 專案目錄: {chart_path.resolve()}")
    print(f"  * 報告附件: {dest_path.resolve()}")
    print("="*80)

if __name__ == "__main__":
    main()
