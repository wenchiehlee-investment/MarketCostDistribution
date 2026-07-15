"""Shim — canonical code lives in skills/skill-market-cost-distribution/scripts/data_loader.py."""
from src._skill_loader import load_skill_module as _load

_impl = _load("data_loader")
DataLoader = _impl.DataLoader
