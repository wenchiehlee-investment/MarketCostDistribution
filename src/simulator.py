"""Shim — canonical code lives in skills/skill-market-cost-distribution/scripts/simulator.py."""
from src._skill_loader import load_skill_module as _load

_impl = _load("simulator")
CostSimulator = _impl.CostSimulator
