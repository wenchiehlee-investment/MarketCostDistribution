"""Shim — canonical code lives in skills/skill-market-cost-distribution/scripts/data_loader.py."""
from pathlib import Path

from src._skill_loader import load_skill_module as _load

_impl = _load("data_loader")

_REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class DataLoader(_impl.DataLoader):
    """Same as the skill's DataLoader, but data_dir defaults to this repo's data/.

    (The skill module resolves its default relative to its own file location,
    which would point inside the deployed skill folder.)
    """

    def __init__(self, data_dir=None):
        super().__init__(data_dir=data_dir if data_dir is not None else _REPO_DATA_DIR)
