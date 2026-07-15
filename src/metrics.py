"""Shim — canonical code lives in skills/skill-market-cost-distribution/scripts/metrics.py."""
from src._skill_loader import load_skill_module as _load

_impl = _load("metrics")
CostMetrics = _impl.CostMetrics
TRUST_LEVELS = _impl.TRUST_LEVELS
LOCKUP_HEAVY = _impl.LOCKUP_HEAVY
average_if_zero = _impl.average_if_zero
