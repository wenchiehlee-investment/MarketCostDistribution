#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
taishin_intraday_simulator.py — 單檔股票模擬入口（薄包裝）

實際邏輯由部署在 skills/skill-market-cost-distribution/ 的技能提供
（單一程式碼來源，與 wenchiehlee/skills 登錄庫同步）。

使用方式：
    python scripts/taishin_intraday_simulator.py 2330
    python scripts/taishin_intraday_simulator.py 2330 --offline

未指定代號時預設 2330。其餘參數原樣轉傳給技能 runner。
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

    args = sys.argv[1:]
    argv = [str(RUNNER)]

    # Leading bare tokens are stock codes; everything from the first flag on
    # is forwarded verbatim (so flag values are never mistaken for codes).
    n_codes = 0
    while n_codes < len(args) and not args[n_codes].startswith("-"):
        n_codes += 1
    codes, rest = args[:n_codes], args[n_codes:]

    if codes:
        argv += ["--symbol"] + codes
    elif "--symbol" not in rest and "--list" not in rest:
        argv += ["--symbol", "2330"]

    if "--data-dir" not in rest:
        argv += ["--data-dir", str(REPO_ROOT / "data")]
    if "--output-dir" not in rest:
        argv += ["--output-dir", str(REPO_ROOT / "output")]
    argv += rest

    sys.argv = argv
    runpy.run_path(str(RUNNER), run_name="__main__")


if __name__ == "__main__":
    main()
