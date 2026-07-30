
import json
import pandas as pd

def calc_expectation(row):
    """
    決算期待度 = (ユーザー予想当期純利益 - 会社予想当期純利益)
               ÷ 会社予想当期純利益 ×100
    """
    try:
        financial = row.get("financial_meta_json", {})
        forecast = row.get("user_forecast_json", {})

        # JSON文字列の場合はdictへ変換
        if isinstance(financial, str):
            financial = json.loads(financial) if financial else {}

        if isinstance(forecast, str):
            forecast = json.loads(forecast) if forecast else {}

        company = financial.get("net_income_forecast")
        user = (
            forecast.get("year1", {})
            .get("net_income")
        )

        if company in [None, "", 0] or user in [None, ""]:
            return None

        return round((user - company) / company * 100, 1)

    except Exception:
        return None
