"""Shared loader for the deployed skill-market-cost-distribution modules.

The canonical implementation lives in skills/skill-market-cost-distribution/scripts/
(synced from the wenchiehlee/skills registry via that folder's self_update.py).
The src/ modules are thin shims that re-export from there so legacy
`from src.X import Y` imports keep working without duplicating any code.
"""
import importlib.util
import sys
from pathlib import Path

_SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "skill-market-cost-distribution" / "scripts"


def load_skill_module(module_name: str):
    """Load a module from the deployed skill's scripts folder (cached in sys.modules)."""
    cache_key = f"_skill_mcd_{module_name}"
    if cache_key in sys.modules:
        return sys.modules[cache_key]

    module_path = _SKILL_SCRIPTS / f"{module_name}.py"
    if not module_path.exists():
        raise ImportError(
            f"Skill module not found: {module_path}\n"
            "請先部署技能：從 wenchiehlee/skills 登錄庫複製 "
            "common/skill-market-cost-distribution 到本 repo 的 skills/ 資料夾，"
            "或在該資料夾內執行 python self_update.py"
        )

    spec = importlib.util.spec_from_file_location(cache_key, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[cache_key] = module
    spec.loader.exec_module(module)
    return module
