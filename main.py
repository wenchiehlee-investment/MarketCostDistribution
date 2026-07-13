import click
import pandas as pd
from pathlib import Path
import sys

# Reconfigure stdout/stderr to handle UTF-8 printing on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Add src/ to python path
sys.path.append(str(Path(__file__).resolve().parent))

from src.data_loader import DataLoader
from src.simulator import CostSimulator
from src.metrics import CostMetrics
from src.visualizer import CostVisualizer

def get_company_name_from_path(data_dir: Path, stock_code: str) -> str:
    """Helper to extract company name from synced raw files or defaults."""
    stock_code_str = str(stock_code).strip()
    performance_csv = data_dir / "Python-Actions.GoodInfo.Analyzer" / "cleaned_performance.csv"
    if performance_csv.exists():
        try:
            df = pd.read_csv(performance_csv, dtype={"stock_code": str})
            df = df[df["stock_code"] == stock_code_str]
            if not df.empty:
                # Find the first row where company_name is not empty and not null
                df_valid = df.dropna(subset=["company_name"])
                if not df_valid.empty:
                    return df_valid.iloc[0]["company_name"]
        except Exception:
            pass
    return "個股"

@click.command()
@click.option("--symbol", "-s", default="2330", help="台灣股票代號 (e.g., 2330)")
@click.option("--bin-size", "-b", type=float, default=None, help="價格 Bin 間距 (未指定則依首日股價的 0.5% 自動計算)")
@click.option("--decay", "-d", type=float, default=1.0, help="週轉率衰減係數 (預設 1.0，大於 1 則籌碼適應變快)")
@click.option("--output-dir", "-o", default="output", help="圖表輸出目錄")
@click.option("--no-chart", is_flag=True, help="是否跳過生成 Matplotlib 圖表")
@click.option("--apply-corp-actions", is_flag=True, default=False, help="是否在模擬中套用除權息價格調整 (若使用已還原之 Yahoo 歷史價格，請勿開啟此項，以免重複調整)")
def main(symbol, bin_size, decay, output_dir, no_chart, apply_corp_actions):
    """
    MarketCostDistribution - 估算市場股東持股成本分佈系統
    """
    click.echo(f"=== 啟動籌碼成本分佈估算 - 股票代號: {symbol} ===")
    
    loader = DataLoader()
    
    # 1. 載入資料
    try:
        df_prices = loader.load_daily_prices(symbol)
        shares_outstanding = loader.load_shares_outstanding(symbol)
        corporate_actions = loader.load_corporate_actions(symbol)
    except Exception as e:
        click.echo(f"[Error] 資料讀取失敗: {e}")
        sys.exit(1)
        
    company_name = get_company_name_from_path(loader.data_dir, symbol)
    click.echo(f"成功載入資料: {company_name} ({symbol})")
    click.echo(f"  歷史價格天數: {len(df_prices)} 天 (時間範圍: {df_prices['Date'].min().strftime('%Y-%m-%d')} 至 {df_prices['Date'].max().strftime('%Y-%m-%d')})")
    click.echo(f"  目前發行股數: {shares_outstanding / 10**8:.2f} 億股")
    click.echo(f"  除權息日程事件: {len(corporate_actions)} 個")

    # 2. 自動計算價格 Bin 大小
    if bin_size is None:
        first_price = df_prices.iloc[0]["Close"]
        # 計算 0.5% 並四捨五入至適當的小數
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
        click.echo(f"自動計算價格 Bin 間距: {bin_size} 元 (約首日收盤價 {first_price} 元的 {raw_size/first_price*100:.2f}%)")
    else:
        click.echo(f"使用手動價格 Bin 間距: {bin_size} 元")

    # 3. 初始化模擬器與運行
    simulator = CostSimulator(bin_size=bin_size, decay_multiplier=decay)
    
    if apply_corp_actions:
        click.echo("開始跑歷史持股移轉與除權息模擬 (套用除權息調整)...")
        simulation_actions = corporate_actions
    else:
        click.echo("開始跑歷史持股移轉與除權息模擬 (跳過除權息調整，因輸入數據已是還原價格)...")
        simulation_actions = []

    history_records = simulator.run_daily_simulation(
        df_prices=df_prices,
        shares_outstanding=shares_outstanding,
        corporate_actions=simulation_actions
    )
    click.echo("模擬完成！")

    # 4. 計算最終指標
    final_dist = simulator.distribution
    last_close = df_prices.iloc[-1]["Close"]
    metrics = CostMetrics.calculate_all(final_dist, last_close)
    
    # 5. 輸出終端文字報告
    click.echo("\n" + "="*50)
    click.echo(f"【市場籌碼持股成本分佈指標報告】")
    click.echo(f"股票名稱: {company_name} ({symbol})")
    click.echo(f"最新收盤價: {last_close:.2f} 元")
    click.echo(f"平均持股成本: {metrics['Average_Cost']:.2f} 元")
    click.echo(f"中位數持股成本: {metrics['Median_Cost']:.2f} 元")
    click.echo(f"最密集籌碼點 (POC): {metrics['POC']:.2f} 元 (佔比 {metrics['POC_Weight']*100:.2f}%)")
    click.echo(f"獲利籌碼佔比 (股價 > 成本): {metrics['Profit_Ratio']*100:.2f}%")
    click.echo(f"套牢籌碼佔比 (股價 < 成本): {metrics['Loss_Ratio']*100:.2f}%")
    click.echo(f"籌碼集中度 (90%籌碼價格寬度): {metrics['Range_90_Width']:.2f} 元 (佔平均價 {metrics['Chip_Concentration_90_Pct']*100:.2f}%)")
    click.echo("-"*50)
    click.echo("成本百分位數分佈:")
    for k, v in sorted(metrics["Percentiles"].items()):
        pct_num = k.split("_")[1]
        click.echo(f"  前 {pct_num}% 股東持股成本低於: {v:.2f} 元")
    click.echo("="*50 + "\n")
    
    # 輸出 ASCII 籌碼分佈直方圖
    ascii_profile = CostVisualizer.draw_ascii_profile(final_dist, width=30)
    click.echo(ascii_profile)

    # 6. 輸出 Matplotlib 圖表
    if not no_chart:
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        chart_path = output_dir_path / f"{symbol}_cost_distribution.png"
        
        # We need historical DataFrame for plotting the price chart
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
        click.echo(f"視覺化圖表已存檔至: {chart_path.resolve()}")
        
        # Export raw cost distribution to CSV (including trust_level)
        csv_path = output_dir_path / f"{symbol}_cost_distribution.csv"
        
        # Calculate trust level
        trust_level = "未知 (Unknown)"
        if "Turnover_Rate" in df_hist.columns:
            avg_turnover_pct = df_hist['Turnover_Rate'].mean() * 100
            lockup_heavy = ["2412", "3045"]
            if symbol in lockup_heavy:
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
        click.echo(f"市場籌碼成本分佈數據已存檔至: {csv_path.resolve()}")



if __name__ == "__main__":
    main()
