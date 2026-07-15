import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.data_loader import DataLoader
from src.simulator import CostSimulator
from src.metrics import CostMetrics
from src._skill_loader import load_skill_module

# Shared helpers live in the deployed skill (single source of truth)
get_company_name = load_skill_module("run_market_cost").get_company_name

# Set font for Traditional Chinese support on Windows
plt.rcParams['font.family'] = 'Microsoft JhengHei'
plt.rcParams['axes.unicode_minus'] = False

def main():
    loader = DataLoader()
    symbol = sys.argv[1] if len(sys.argv) > 1 else "2330"
    company_name = get_company_name(loader.data_dir, symbol)

    # Load data
    df_prices = loader.load_daily_prices(symbol)
    shares_outstanding = loader.load_shares_outstanding(symbol)

    # Run simulation
    simulator = CostSimulator(bin_size=5.0)
    history_records = simulator.run_daily_simulation(df_prices, shares_outstanding, [])

    # Unified trust level (shared with the skill's outputs)
    trust = CostMetrics.evaluate_trust(
        df_history=pd.DataFrame(history_records),
        total_trading_days=len(df_prices),
        stock_code=symbol,
        data_as_of=df_prices.iloc[-1]["Date"]
    )
    trust_level = trust["label"]
    
    # Calculate metrics
    final_dist = simulator.distribution
    last_close = df_prices.iloc[-1]["Close"]
    metrics = CostMetrics.calculate_all(final_dist, last_close)
    
    # Create plot
    plt.close('all')
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Sort bins
    sorted_bins = sorted(final_dist.items(), key=lambda x: x[0])
    prices = np.array([item[0] for item in sorted_bins])
    weights = np.array([item[1] for item in sorted_bins])
    
    # We filter out bins with very small weights to make the diagram clean and readable
    mask = weights >= 0.0005 # at least 0.05%
    prices = prices[mask]
    weights = weights[mask]
    
    # Convert weights to percentage
    pct_weights = weights * 100
    
    # Colors: Green for profitable (cost <= current close), Red for loss
    colors = ["#2ca02c" if p <= last_close else "#d62728" for p in prices]
    
    # Plot horizontal bar chart
    bars = ax.barh(prices, pct_weights, height=4.0, color=colors, alpha=0.85, edgecolor='none')
    
    # Add values on the bars for the top bins to show exact percentages
    # We label bars that have a weight >= 1.0%
    for idx, (p, w) in enumerate(zip(prices, pct_weights)):
        if w >= 0.5: # Label bins with >= 0.5% weight
            ax.text(w + 0.05, p, f"{w:.1f}%", va='center', ha='left', fontsize=8, color='#333333')
            
    # Draw reference lines
    avg_cost = metrics["Average_Cost"]
    poc = metrics["POC"]
    
    ax.axhline(last_close, color="#1f77b4", linestyle="-", linewidth=1.5, label=f"最新收盤價 (Current Close): {last_close:.2f} 元")
    ax.axhline(avg_cost, color="orange", linestyle="--", linewidth=1.5, label=f"平均持股成本 (Average Cost): {avg_cost:.2f} 元")
    ax.axhline(poc, color="magenta", linestyle=":", linewidth=1.5, label=f"最密集籌碼點 (POC): {poc:.2f} 元 ({pct_weights[prices == poc][0]:.1f}%)")
    
    # Chart styling
    ax.set_title(f"{company_name} ({symbol}) 市場股東持股成本百分比分佈圖", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("持股佔比 (%)", fontsize=12)
    ax.set_ylabel("持股成本價格 (NTD)", fontsize=12)
    ax.set_xlim(0, max(pct_weights) * 1.15)
    
    # Set y ticks to show major price intervals
    ax.set_ylim(min(prices) - 50, max(prices) + 50)
    
    # Legend
    ax.legend(loc="upper right", frameon=True, facecolor='white', framealpha=0.9)
    
    # Add stats textbox
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
    
    output_path = Path(__file__).resolve().parent.parent / "output" / f"{symbol}_cost_distribution_percentage.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close('all')
    print(f"Successfully generated percentage distribution chart at: {output_path}")

if __name__ == "__main__":
    main()
