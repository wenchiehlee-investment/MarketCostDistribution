"""Shim — canonical code lives in skills/skill-market-cost-distribution/scripts/visualizer.py."""
from src._skill_loader import load_skill_module as _load

_impl = _load("visualizer")
CostVisualizer = _impl.CostVisualizer
