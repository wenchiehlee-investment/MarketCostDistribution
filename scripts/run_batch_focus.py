import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Reconfigure stdout for UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

# Add repo root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.data_loader import DataLoader
from src.simulator import CostSimulator
from src.metrics import CostMetrics
from src.visualizer import CostVisualizer

# Force Microsoft JhengHei for Chinese support in matplotlib
plt.rcParams['font.family'] = 'Microsoft JhengHei'
plt.rcParams['axes.unicode_minus'] = False

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
    loader = DataLoader()
    
    # Paths
    repo_root = Path(__file__).resolve().parent.parent
    focus_csv = Path("C:/Users/WJLEE/SynologyDrive/NAS/github.com/biztrends.TW/StockID_TWSE_TPEX_focus.csv")
    output_dir = repo_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    artifact_dir = Path("C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    if not focus_csv.exists():
        print(f"Focus list CSV not found at: {focus_csv}")
        return
        
    df_focus = pd.read_csv(focus_csv, dtype={"代號": str})
    print(f"Loaded {len(df_focus)} stocks from focus list.")
    
    results = []
    
    for idx, row in df_focus.iterrows():
        symbol = str(row["代號"]).strip()
        name_from_csv = str(row["名稱"]).strip()
        
        # Load correct company name
        company_name = get_company_name(loader.data_dir, symbol)
        if company_name == "個股":
            company_name = name_from_csv
            
        print(f"[{idx+1}/{len(df_focus)}] Processing {company_name} ({symbol})...")
        
        try:
            # 1. Load data
            df_prices = loader.load_daily_prices(symbol)
            shares_outstanding = loader.load_shares_outstanding(symbol)
            shareholder_concentration = loader.load_weekly_shareholder_concentration(symbol)
            
            # 2. Run simulation
            simulator = CostSimulator(bin_size=5.0)
            history_records = simulator.run_daily_simulation(
                df_prices, 
                shares_outstanding, 
                [], 
                shareholder_concentration=shareholder_concentration,
                stock_code=symbol
            )
            
            # 3. Calculate metrics
            final_dist = simulator.distribution
            last_close = df_prices.iloc[-1]["Close"]
            metrics = CostMetrics.calculate_all(final_dist, last_close)
            
            # Calculate trust level
            df_prices['Turnover'] = df_prices['Volume'] / shares_outstanding
            avg_turnover_pct = df_prices['Turnover'].mean() * 100
            
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
                
            # 4. Generate dual-panel chart
            chart_path = output_dir / f"{symbol}_cost_distribution.png"
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
            
            # 5. Generate percentage chart
            plt.close('all')
            fig, ax = plt.subplots(figsize=(10, 8))
            sorted_bins = sorted(final_dist.items(), key=lambda x: x[0])
            prices_arr = np.array([item[0] for item in sorted_bins])
            weights_arr = np.array([item[1] for item in sorted_bins])
            
            # Filter out tiny weights
            mask = weights_arr >= 0.0005
            prices_arr = prices_arr[mask]
            weights_arr = weights_arr[mask]
            pct_weights = weights_arr * 100
            
            colors = ["#2ca02c" if p <= last_close else "#d62728" for p in prices_arr]
            
            # Plot
            bin_size = prices_arr[1] - prices_arr[0] if len(prices_arr) > 1 else 1.0
            bars = ax.barh(prices_arr, pct_weights, height=bin_size * 0.85, color=colors, alpha=0.85, edgecolor='none')
            
            # Add text labels on bars
            for p_val, w_val in zip(prices_arr, pct_weights):
                if w_val >= 0.5:
                    ax.text(w_val + 0.05, p_val, f"{w_val:.1f}%", va='center', ha='left', fontsize=8, color='#333333')
                    
            avg_cost = metrics["Average_Cost"]
            poc = metrics["POC"]
            
            ax.axhline(last_close, color="#1f77b4", linestyle="-", linewidth=1.5, label=f"最新收盤價 (Current Close): {last_close:.2f} 元")
            ax.axhline(avg_cost, color="orange", linestyle="--", linewidth=1.5, label=f"平均持股成本 (Average Cost): {avg_cost:.2f} 元")
            
            # Find weight of POC
            poc_weight = 0.0
            if len(pct_weights[prices_arr == poc]) > 0:
                poc_weight = pct_weights[prices_arr == poc][0]
            ax.axhline(poc, color="magenta", linestyle=":", linewidth=1.5, label=f"最密集籌碼點 (POC): {poc:.2f} 元 ({poc_weight:.1f}%)")
            
            ax.set_title(f"{company_name} ({symbol}) 市場股東持股成本百分比分佈圖", fontsize=14, fontweight='bold', pad=15)
            ax.set_xlabel("持股佔比 (%)", fontsize=12)
            ax.set_ylabel("持股成本價格 (NTD)", fontsize=12)
            ax.set_xlim(0, max(pct_weights) * 1.15)
            ax.set_ylim(min(prices_arr) - bin_size * 5, max(prices_arr) + bin_size * 5)
            ax.legend(loc="upper right", frameon=True, facecolor='white', framealpha=0.9)
            
            stats_text = (
                f"【統計數據摘要】\n"
                f"最新股價: {last_close:.1f} 元\n"
                f"平均成本: {avg_cost:.1f} 元\n"
                f"中位成本: {metrics['Median_Cost']:.1f} 元\n"
                f"獲利籌碼比率: {metrics['Profit_Ratio']*100:.1f}%\n"
                f"套牢籌碼比率: {metrics['Loss_Ratio']*100:.1f}%\n"
                f"籌碼集中度(90%區間): {metrics['Range_90_Width']:.1f} 元\n"
                f"模型可信度: {trust_level}"
            )
            props = dict(boxstyle='round', facecolor='#f5f5f5', alpha=0.9, edgecolor='#cccccc')
            ax.text(0.97, 0.05, stats_text, transform=ax.transAxes, fontsize=10,
                    verticalalignment='bottom', horizontalalignment='right', bbox=props)
            
            plt.tight_layout()
            perc_chart_path = output_dir / f"{symbol}_cost_distribution_percentage.png"
            plt.savefig(perc_chart_path, dpi=150, bbox_inches='tight')
            plt.close('all')
            
            # Export raw cost distribution to CSV (including trust_level)
            csv_path = output_dir / f"{symbol}_cost_distribution.csv"
            dist_data = [{"price": k, "weight": v, "trust_level": trust_level} for k, v in sorted(final_dist.items())]
            df_dist = pd.DataFrame(dist_data)
            df_dist.to_csv(csv_path, index=False)
            
            # 6. Copy to artifact dir
            dest_dual = artifact_dir / f"{symbol}_cost_distribution.png"
            dest_perc = artifact_dir / f"{symbol}_cost_distribution_percentage.png"
            dest_csv = artifact_dir / f"{symbol}_cost_distribution.csv"
            
            # Python copy
            import shutil
            shutil.copy(str(chart_path), str(dest_dual))
            shutil.copy(str(perc_chart_path), str(dest_perc))
            shutil.copy(str(csv_path), str(dest_csv))

            
            results.append({
                "Symbol": symbol,
                "Name": company_name,
                "Close": last_close,
                "AvgCost": avg_cost,
                "MedianCost": metrics["Median_Cost"],
                "POC": f"{poc:.2f} ({poc_weight:.1f}%)",
                "ProfitRatio": metrics["Profit_Ratio"] * 100,
                "LossRatio": metrics["Loss_Ratio"] * 100,
                "TrustLevel": trust_level
            })
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            
    # Write report
    write_focus_report(results, artifact_dir)
    print("All processing completed successfully!")

def write_focus_report(results, artifact_dir):
    report_path = artifact_dir / "market_cost_distribution_focus_report.md"
    
    # Build Table
    table_lines = [
        "| 股票代號與名稱 | 最新收盤價 (元) | 平均持股成本 (元) | 中位持股成本 (元) | 最密集籌碼點 POC | 獲利籌碼佔比 | 套牢籌碼佔比 | 模型可信度 (Trust Level) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    carousel_slides = []
    
    for r in results:
        table_lines.append(
            f"| **{r['Symbol']} {r['Name']}** | {r['Close']:.2f} | {r['AvgCost']:.2f} | {r['MedianCost']:.2f} | {r['POC']} | {r['ProfitRatio']:.2f}% | {r['LossRatio']:.2f}% | **{r['TrustLevel']}** |"
        )
        carousel_slides.append(
            f"![{r['Name']} {r['Symbol']} 籌碼成本百分比分佈圖](C:/Users/WJLEE/.gemini/antigravity-cli/brain/c6ed6e82-c0d0-4205-9fb2-70a534bd7919/{r['Symbol']}_cost_distribution_percentage.png)"
        )
        
    carousel_content = "\n<!-- slide -->\n".join(carousel_slides)
    
    markdown_content = f"""# 觀察名單籌碼持股成本分佈評估報告 (Focus List)

本報告包含您的觀察名單（共 {len(results)} 檔）所有市場持股成本分佈的模擬結果與可信度評估。

---

## 一、 觀察名單數據總覽

以下為所有觀察名單股票的最新持股成本分析結果：

{"\n".join(table_lines)}

---

## 二、 觀察名單籌碼百分比分佈圖 (Carousel)

您可以使用下方 Carousel 快速滑動瀏覽所有觀察名單的持股成本百分比分佈圖：

````carousel
{carousel_content}
````

報告生成時間：2026-07-13
"""
    
    report_path.write_text(markdown_content, encoding='utf-8')
    print(f"Focus report saved to: {report_path}")

if __name__ == "__main__":
    main()
