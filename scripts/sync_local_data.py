import shutil
from pathlib import Path
import subprocess
import sys

def run_git_pull(repo_path: Path) -> bool:
    if not repo_path.exists():
        print(f"[Warning] Repository path does not exist: {repo_path}")
        return False
    
    print(f"Executing git pull in: {repo_path}")
    try:
        # Use subprocess to run git pull
        result = subprocess.run(
            ["git", "pull"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            print("  Git pull successful!")
            if result.stdout.strip():
                print(f"  Output:\n{result.stdout.strip()}")
            return True
        else:
            print(f"  [Error] Git pull failed with code {result.returncode}")
            print(f"  Error message:\n{result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"  [Error] Failed to execute git pull: {e}")
        return False

def main():
    repo_root = Path(__file__).resolve().parent.parent
    workspace_root = repo_root.parent

    # Adjacent upstream repository paths
    yahoo_repo = workspace_root / "Yahoo.Finance"
    goodinfo_repo = workspace_root / "Python-Actions.GoodInfo.Analyzer"

    print("=== Step 1: Pulling Upstream Repositories ===")
    run_git_pull(yahoo_repo)
    run_git_pull(goodinfo_repo)
    print("=============================================\n")

    # Source files in adjacent repositories
    sources = {
        "Yahoo Finance Daily Price": (
            yahoo_repo / "data" / "reports" / "raw_yahoo_finance_daily_price.csv",
            repo_root / "data" / "Yahoo.Finance" / "raw_yahoo_finance_daily_price.csv"
        ),
        "GoodInfo Daily K-Line Flow": (
            goodinfo_repo / "data" / "stage1_raw" / "raw_daily_k_chart_flow.csv",
            repo_root / "data" / "Python-Actions.GoodInfo.Analyzer" / "raw_daily_k_chart_flow.csv"
        ),
        "GoodInfo Cleaned Dividends": (
            goodinfo_repo / "data" / "stage2_cleaned" / "cleaned_dividends.csv",
            repo_root / "data" / "Python-Actions.GoodInfo.Analyzer" / "cleaned_dividends.csv"
        ),
        "GoodInfo Cleaned Dividend Schedule": (
            goodinfo_repo / "data" / "stage2_cleaned" / "cleaned_dividend_schedule.csv",
            repo_root / "data" / "Python-Actions.GoodInfo.Analyzer" / "cleaned_dividend_schedule.csv"
        ),
        "GoodInfo Cleaned Performance": (
            goodinfo_repo / "data" / "stage2_cleaned" / "cleaned_performance.csv",
            repo_root / "data" / "Python-Actions.GoodInfo.Analyzer" / "cleaned_performance.csv"
        ),
    }

    print("=== Step 2: Copying Synced Data Locally ===")
    for name, (src, dest) in sources.items():
        if not src.exists():
            print(f"[Warning] Source file not found for {name} at: {src}")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"Copying {name}...")
        try:
            shutil.copy2(src, dest)
            print(f"  Done. Size: {dest.stat().st_size / (1024*1024):.2f} MB")
        except Exception as e:
            print(f"  [Error] Copy failed: {e}")
    
    print("\nData sync completed successfully!")

if __name__ == "__main__":
    # Fix stdout encoding to UTF-8 on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
