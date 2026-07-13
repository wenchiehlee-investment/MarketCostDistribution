# Market Cost Distribution Raw Column Definition

This file defines the schema of the generated market cost distribution CSV files (`*_cost_distribution.csv`) so that downstream repositories (such as `biztrends.TW` and `mkdocs-investment`) can easily consume the estimated cost data.

## File Format & Location
* **Filename Pattern**: `{stock_code}_cost_distribution.csv` (e.g. `2330_cost_distribution.csv`)
* **Location**: `output/` directory inside `MarketCostDistribution`.

---

## Schema definition

| Column Name | Data Type | Description |
| :--- | :---: | :--- |
| **price** | Float | The transaction price bin (in NTD). The pricing bin interval (e.g. 0.05, 0.1, 0.5, 1.0, 5.0) is dynamically computed based on the stock's first-day close price to balance resolution and computational efficiency. |
| **weight** | Float | The estimated proportion of outstanding shares held at this price bin (represented as a ratio between `0.0` and `1.0`). The sum of all weights in a single CSV file is normalized to exactly `1.0`. |

---

## How to load and use in Python

You can easily read the CSV data and plot the distribution or calculate metrics using pandas:

```python
import pandas as pd

# Load the distribution data
df_dist = pd.read_csv("2330_cost_distribution.csv")

# 1. Reconstruct Average Cost
average_cost = (df_dist["price"] * df_dist["weight"]).sum()
print(f"Average Cost: {average_cost:.2f} NTD")

# 2. Get Point of Control (POC - price with the highest share concentration)
poc_row = df_dist.loc[df_dist["weight"].idxmax()]
print(f"POC Price: {poc_row['price']:.2f} NTD (Weight: {poc_row['weight']*100:.2f}%)")

# 3. Calculate Profit Ratio given a current close price
current_close = 2415.00
profit_ratio = df_dist[df_dist["price"] < current_close]["weight"].sum()
print(f"Profit Ratio: {profit_ratio*100:.2f}%")
```
