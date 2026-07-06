
import pandas as pd


def get_alert_status(row):
    price = row["current_price"]
    buy = row["buy_target"]
    sell = row["sell_target"]
    if pd.notna(buy):
        if price <= buy:
            return "🟢買い"
    if pd.notna(sell):
        if price >= sell:
            return "🔴売り"
    return ""
