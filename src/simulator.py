import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

class CostSimulator:
    """
    CostSimulator runs the chronological simulation of the market cost distribution.
    It supports:
    - Proportional decay based on daily turnover rate.
    - Ex-dividend/Ex-rights adjustments.
    - Dynamic bin sizing.
    - Hourly intraday data distribution (optional).
    """
    def __init__(self, bin_size: float = 0.5, decay_multiplier: float = 1.0):
        self.bin_size = bin_size
        self.decay_multiplier = decay_multiplier
        # The cost distribution is represented as a dict: {price_bin: weight}
        # where sum(weights) = 1.0 (100%)
        self.distribution: Dict[float, float] = {}

    def get_bin(self, price: float) -> float:
        """Finds the nearest bin center for a given price."""
        return round(price / self.bin_size) * self.bin_size

    def initialize_distribution(self, price: float):
        """Initializes 100% of the distribution at a single price point."""
        bin_center = self.get_bin(price)
        self.distribution = {bin_center: 1.0}

    def apply_turnover_decay(self, turnover_rate: float) -> float:
        """
        Decays all existing bins by (1 - turnover_rate * decay_multiplier).
        Returns the total weight removed, which is then added to the new transaction price bin.
        """
        # Clip turnover rate to a sane range [0.0, 1.0]
        actual_decay = min(max(turnover_rate * self.decay_multiplier, 0.0), 1.0)
        
        removed_weight = 0.0
        new_dist = {}
        for price_bin, weight in self.distribution.items():
            decayed_weight = weight * (1.0 - actual_decay)
            removed_weight += weight * actual_decay
            if decayed_weight > 1e-7: # Filter out tiny dust weights
                new_dist[price_bin] = decayed_weight
                
        self.distribution = new_dist
        return removed_weight

    def add_new_cost(self, price: float, weight: float):
        """Adds a new cost chunk at the specified price bin."""
        if weight <= 0.0:
            return
        bin_center = self.get_bin(price)
        self.distribution[bin_center] = self.distribution.get(bin_center, 0.0) + weight

    def apply_corporate_action(self, cash_dividend: float, stock_dividend_ratio: float):
        """
        Adjusts all price bins in the distribution for cash dividends and stock splits/dividends:
        New_Price = (Old_Price - cash_dividend) / (1 + stock_dividend_ratio)
        Then aggregates the adjusted weights onto the standard price grid.
        """
        if cash_dividend == 0.0 and stock_dividend_ratio == 0.0:
            return

        new_dist = {}
        for price_bin, weight in self.distribution.items():
            # Apply adjustment formula
            adjusted_price = (price_bin - cash_dividend) / (1.0 + stock_dividend_ratio)
            # Find new bin center
            new_bin = self.get_bin(adjusted_price)
            # Aggregate weight
            new_dist[new_bin] = new_dist.get(new_bin, 0.0) + weight
            
        self.distribution = new_dist

    def run_daily_simulation(
        self, 
        df_prices: pd.DataFrame, 
        shares_outstanding: float, 
        corporate_actions: List[Dict]
    ) -> List[Dict]:
        """
        Runs the daily simulation step-by-step.
        df_prices columns: Date, Open, High, Low, Close, Volume
        corporate_actions: List of dicts with keys Date, Cash_Dividend, Stock_Dividend_Ratio
        
        Returns a time series of daily distribution snapshots and metrics.
        """
        # Convert corporate actions to a dictionary keyed by date string for O(1) lookup
        actions_by_date = {
            act["Date"].strftime("%Y-%m-%d"): act for act in corporate_actions
        }

        history_records = []
        
        for idx, row in df_prices.iterrows():
            date_str = row["Date"].strftime("%Y-%m-%d")
            close_price = row["Close"]
            high_price = row["High"]
            low_price = row["Low"]
            volume = row["Volume"]
            
            # 1. Check for corporate actions on this day *before* applying daily trading
            # In Taiwan, stock prices open ex-dividend/ex-rights on the Ex-date.
            # So the adjustment must be applied to the *existing* distribution *before* incorporating today's trades.
            if date_str in actions_by_date:
                action = actions_by_date[date_str]
                self.apply_corporate_action(
                    cash_dividend=action["Cash_Dividend"],
                    stock_dividend_ratio=action["Stock_Dividend_Ratio"]
                )

            # 2. Estimate VWAP
            # If High and Low are available, use the simple VWAP approximation: (H + L + C) / 3
            if pd.notna(high_price) and pd.notna(low_price) and high_price > 0 and low_price > 0:
                vwap = (high_price + low_price + close_price) / 3.0
            else:
                vwap = close_price
                
            # 3. Calculate Turnover Rate
            if shares_outstanding > 0:
                turnover_rate = volume / shares_outstanding
            else:
                turnover_rate = 0.02 # fallback to 2% if missing
                
            # Clip turnover rate to prevent extreme anomalies
            turnover_rate = min(max(turnover_rate, 0.0), 0.20)

            # 4. Update the distribution
            if not self.distribution:
                # First day initialization
                self.initialize_distribution(vwap)
            else:
                # Normal update: decay old holders and add today's VWAP bucket
                removed_weight = self.apply_turnover_decay(turnover_rate)
                self.add_new_cost(vwap, removed_weight)
                
            # 5. Normalize (to prevent floating point drift)
            total_weight = sum(self.distribution.values())
            if total_weight > 0:
                self.distribution = {k: v / total_weight for k, v in self.distribution.items()}
                
            # 6. Store daily snapshot (deep copy of distribution)
            snapshot = {k: v for k, v in self.distribution.items() if v > 1e-5}
            
            history_records.append({
                "Date": row["Date"],
                "Close": close_price,
                "VWAP": vwap,
                "Turnover_Rate": turnover_rate,
                "Distribution": snapshot
            })
            
        return history_records

    def run_hourly_simulation(
        self,
        df_hourly: pd.DataFrame,
        shares_outstanding: float,
        corporate_actions: List[Dict]
    ) -> List[Dict]:
        """
        Runs simulation using hourly intraday data.
        df_hourly columns: Date (Timestamp containing hour), Open, High, Low, Close, Volume
        
        This distributes the day's volume across price levels using hourly candles,
        providing a much more accurate cost distribution (Intraday Volume Profile).
        """
        # Sort by hourly date
        df_hourly = df_hourly.sort_values("Date").reset_index(drop=True)
        
        # We still apply corporate actions daily. Ex-dates apply on the first hour of that date.
        actions_by_date = {
            act["Date"].strftime("%Y-%m-%d"): act for act in corporate_actions
        }
        
        history_records = []
        applied_actions_dates = set()
        
        # Group by day to report daily summaries, but simulate hour-by-hour
        df_hourly["Day_Str"] = df_hourly["Date"].dt.strftime("%Y-%m-%d")
        
        for day_str, day_group in df_hourly.groupby("Day_Str"):
            # Check corporate action for this day
            if day_str in actions_by_date and day_str not in applied_actions_dates:
                action = actions_by_date[day_str]
                self.apply_corporate_action(
                    cash_dividend=action["Cash_Dividend"],
                    stock_dividend_ratio=action["Stock_Dividend_Ratio"]
                )
                applied_actions_dates.add(day_str)
                
            day_volume = 0.0
            day_close = day_group.iloc[-1]["Close"]
            
            for _, hour_row in day_group.iterrows():
                h_close = hour_row["Close"]
                h_high = hour_row["High"]
                h_low = hour_row["Low"]
                h_volume = hour_row["Volume"]
                day_volume += h_volume
                
                # Hourly VWAP
                h_vwap = (h_high + h_low + h_close) / 3.0 if (h_high > 0 and h_low > 0) else h_close
                
                # Hourly turnover
                h_turnover = h_volume / shares_outstanding if shares_outstanding > 0 else 0.002
                h_turnover = min(max(h_turnover, 0.0), 0.05) # Hourly cap
                
                # Update
                if not self.distribution:
                    self.initialize_distribution(h_vwap)
                else:
                    removed = self.apply_turnover_decay(h_turnover)
                    self.add_new_cost(h_vwap, removed)
                    
            # Normalize daily
            total_weight = sum(self.distribution.values())
            if total_weight > 0:
                self.distribution = {k: v / total_weight for k, v in self.distribution.items()}
                
            snapshot = {k: v for k, v in self.distribution.items() if v > 1e-5}
            
            history_records.append({
                "Date": pd.to_datetime(day_str),
                "Close": day_close,
                "VWAP": day_close, # fallback representation
                "Turnover_Rate": day_volume / shares_outstanding if shares_outstanding > 0 else 0.0,
                "Distribution": snapshot
            })
            
        return history_records
