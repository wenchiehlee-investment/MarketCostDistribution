import shutil
from pathlib import Path

def main():
    repo_root = Path(__file__).resolve().parent.parent
    workspace_root = repo_root.parent

    # Source files in adjacent repositories
    sources = {
        "Yahoo Finance Daily Price": (
            workspace_root / "Yahoo.Finance" / "data" / "reports" / "raw_yahoo_finance_daily_price.csv",
            repo_root / "data" / "Yahoo.Finance" / "raw_yahoo_finance_daily_price.csv"
        ),
        "GoodInfo Daily K-Line Flow": (
            workspace_root / "Python-Actions.GoodInfo.Analyzer" / "data" / "stage1_raw" / "raw_daily_k_chart_flow.csv",
            repo_root / "data" / "Python-Actions.GoodInfo.Analyzer" / "raw_daily_k_chart_flow.csv"
        ),
        "GoodInfo Cleaned Dividends": (
            workspace_root / "Python-Actions.GoodInfo.Analyzer" / "data" / "stage2_cleaned" / "cleaned_dividends.csv",
            repo_root / "data" / "Python-Actions.GoodInfo.Analyzer" / "cleaned_dividends.csv"
        ),
        "GoodInfo Cleaned Dividend Schedule": (
            workspace_root / "Python-Actions.GoodInfo.Analyzer" / "data" / "stage2_cleaned" / "cleaned_dividend_schedule.csv",
            repo_root / "data" / "Python-Actions.GoodInfo.Analyzer" / "cleaned_dividend_schedule.csv"
        ),
        "GoodInfo Cleaned Performance": (
            workspace_root / "Python-Actions.GoodInfo.Analyzer" / "data" / "stage2_cleaned" / "cleaned_performance.csv",
            repo_root / "data" / "Python-Actions.GoodInfo.Analyzer" / "cleaned_performance.csv"
        ),
    }

    print("=== Copying Upstream Data Locally for Testing ===")
    for name, (src, dest) in sources.items():
        if not src.exists():
            print(f"[Warning] Source not found for {name} at: {src}")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"Copying {name}...")
        print(f"  From: {src}")
        print(f"  To:   {dest}")
        shutil.copy2(src, dest)
        print(f"Finished copying {name} ({dest.stat().st_size / (1024*1024):.2f} MB)")
    
    print("\nData sync completed successfully!")

if __name__ == "__main__":
    main()
