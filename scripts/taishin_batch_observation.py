#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
taishin_batch_observation.py — 觀察名單批次入口（薄包裝）

實際邏輯由部署在 skills/skill-market-cost-distribution/ 的技能提供
（單一程式碼來源，與 wenchiehlee/skills 登錄庫同步）。

預設等同於：
    python skills/skill-market-cost-distribution/scripts/run_market_cost.py \
        --list StockID_TWSE_TPEX.csv --data-dir data --output-dir output

額外參數會原樣轉傳給技能 runner（例如 --offline、--symbol 2330）。
"""
import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "skills" / "skill-market-cost-distribution" / "scripts" / "run_market_cost.py"


def main():
    if not RUNNER.exists():
        print(f"[Error] 找不到技能 runner: {RUNNER}")
        print("請先部署技能（skills/skill-market-cost-distribution/），"
              "或在該資料夾內執行 python self_update.py")
        sys.exit(1)

    passthrough = sys.argv[1:]
    argv = [str(RUNNER)]
    if not any(a in ("--list", "--symbol") for a in passthrough):
        argv += ["--list", str(REPO_ROOT / "StockID_TWSE_TPEX.csv")]
    if "--data-dir" not in passthrough:
        argv += ["--data-dir", str(REPO_ROOT / "data")]
    if "--output-dir" not in passthrough:
        argv += ["--output-dir", str(REPO_ROOT / "output")]
    argv += passthrough

    sys.argv = argv
    runpy.run_path(str(RUNNER), run_name="__main__")


if __name__ == "__main__":
    main()
