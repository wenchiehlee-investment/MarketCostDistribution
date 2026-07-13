import numpy as np
from typing import Dict, List, Tuple, Optional

class CostMetrics:
    """
    CostMetrics calculates statistical and trading metrics from a cost distribution.
    """
    @staticmethod
    def calculate_all(distribution: Dict[float, float], current_price: float) -> Dict:
        """
        Calculates all key metrics for a given cost distribution and current price.
        """
        if not distribution:
            return {}

        # Sort distribution items by price
        sorted_bins = sorted(distribution.items(), key=lambda x: x[0])
        prices = np.array([item[0] for item in sorted_bins])
        weights = np.array([item[1] for item in sorted_bins])
        
        # Ensure weights are normalized
        sum_weights = weights.sum()
        if sum_weights > 0:
            weights = weights / sum_weights

        # 1. Average Cost
        avg_cost = float(np.sum(prices * weights))

        # Cumulative weight
        cum_weights = np.cumsum(weights)

        # 2. Percentiles (10%, 25%, 50%, 75%, 90%)
        percentiles = {}
        target_pcts = [0.10, 0.25, 0.50, 0.75, 0.90]
        for pct in target_pcts:
            # Find the first index where cumulative weight >= pct
            idx = np.searchsorted(cum_weights, pct)
            if idx >= len(prices):
                idx = len(prices) - 1
            percentiles[f"Pct_{int(pct*100)}"] = float(prices[idx])

        # Median cost is Pct_50
        median_cost = percentiles["Pct_50"]

        # 3. Profit Ratio (cost < current_price)
        # In Taiwan, we usually count cost <= current_price as profit.
        profit_idx = prices <= current_price
        profit_ratio = float(np.sum(weights[profit_idx]))

        # Loss Ratio
        loss_ratio = 1.0 - profit_ratio

        # 4. Point of Control (POC) - price bin with maximum weight
        max_idx = np.argmax(weights)
        poc = float(prices[max_idx])
        poc_weight = float(weights[max_idx])

        # 5. Chip Concentration (籌碼集中度)
        # e.g., range between 15% and 85% of cumulative weight,
        # or range between 10% and 90%
        range_90_width = percentiles["Pct_90"] - percentiles["Pct_10"]
        range_90_pct = range_90_width / average_if_zero(avg_cost)

        return {
            "Average_Cost": avg_cost,
            "Median_Cost": median_cost,
            "Percentiles": percentiles,
            "Profit_Ratio": profit_ratio,
            "Loss_Ratio": loss_ratio,
            "POC": poc,
            "POC_Weight": poc_weight,
            "Range_90_Width": range_90_width,
            "Chip_Concentration_90_Pct": range_90_pct
        }

def average_if_zero(val: float) -> float:
    return val if val != 0.0 else 1.0
