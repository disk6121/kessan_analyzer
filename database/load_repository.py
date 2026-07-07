import json
import supabase
import streamlit as st

from database.supabase_client import supabase



def load_json(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value      # Supabase
    return json.loads(value)   # SQLite


def load_company(ticker):

    result = (
        supabase
        .table("companies")
        .select("annual_perf_json")
        .eq("ticker", ticker)
        .execute()
    )

    if result.data:
        return result.data[0].get("annual_perf_json") or {}
    return {}



def load_analysis_data(ticker):

    row_result = (
        supabase
        .table("initial_data")
        .select(
        "combined_data_json, seg_data_json, ai_deep_dive_json, deep_dive_memo, peer_comparison_json"
        )
        .eq("ticker", ticker)
        .execute()
    )

    meta_result = (
        supabase
        .table("companies")
        .select("*")
        .eq("ticker", ticker)
        .execute()
    )

    row_data = row_result.data[0] if row_result.data else None
    meta_row = meta_result.data[0] if meta_result.data else None

    return row_data, meta_row


def load_common_note():

    result = (
        supabase
        .table("app_settings")
        .select("setting_value")
        .eq("setting_key", "common_note")
        .execute()
    )

    if result.data:
        return result.data[0].get("setting_value", "")

    return ""



def load_existing_quarter_data(ticker):

    result1 = (
        supabase
        .table("initial_data")
        .select(
            "combined_data_json, "
            "seg_data_json, "
            "ai_deep_dive_json, "
            "deep_dive_memo, "
            "peer_comparison_json"
        )
        .eq("ticker", ticker)
        .execute()
    )

    result2 = (
        supabase
        .table("companies")
        .select(
            "annual_perf_json, "
            "user_forecast_json"
        )
        .eq("ticker", ticker)
        .execute()
    )

    row1 = result1.data[0] if result1.data else None
    row2 = result2.data[0] if result2.data else None

    if row1 and row2:
        return {
            "combined": row1.get("combined_data_json") or {},
            "seg": row1.get("seg_data_json") or {},
            "reports": row1.get("ai_deep_dive_json") or {},
            "deep_dive_memo": row1.get("deep_dive_memo") or "",
            "peer_comparison": row1.get("peer_comparison_json") or {},
            "annual_perf": row2.get("annual_perf_json") or {},
            "user_forecast": row2.get("user_forecast_json") or {}
        }

    return None



def load_peer_summary(ticker):

    """
    保存済みデータから比較表用データを取得
    """
    row_data, meta_row = load_analysis_data(ticker)
    if row_data is None or meta_row is None:
      return None

    meta1 = load_json(meta_row["annual_perf_json"])
    current = meta1.get("current_year_actual_or_forecast", {})
    sales = float(current.get("revenue") or 0)
    op = float(current.get("operating_income") or 0)

    margin = ""
    if sales:
      margin = f"{op/sales*100:.1f}%"

    def safe_float(x):
        try:
            return float(x)
        except:
            return None
    meta2 = load_json(meta_row["financial_meta_json"])
    shares_issued = safe_float(meta2.get("shares_issued")) or 0
    treasury_shares = safe_float(meta2.get("treasury_shares")) or 0
    ns_shares = shares_issued - treasury_shares
    price = safe_float(meta_row["current_price"]) if meta_row else None
    ap_forecast = {}
    if meta_row["user_forecast_json"]:
        ap_forecast = load_json(meta_row["user_forecast_json"])
    year1 = ap_forecast.get("year1", {})
    user_fc_net_income = safe_float(year1.get("net_income"))
    user_fc_per = None
    if (
        user_fc_net_income is not None
        and user_fc_net_income > 0
        and ns_shares > 0
    ):
        user_fc_eps = (user_fc_net_income / ns_shares) * 1000000
        user_fc_per = price / user_fc_eps
    financial_meta = load_json(meta_row["financial_meta_json"])
    exchange_name = financial_meta.get("exchange_name") if financial_meta else "不明"

    return {
      "会社名": meta_row["company_name"],
      "証券コード": ticker,
      "上場区分": exchange_name,
      "PER": f"{float(meta_row["per"]):.2f}" if meta_row["per"] else "",
      "独自予想PER": f"{float(user_fc_per):.2f}" if user_fc_per else "",
      "PBR": f"{float(meta_row["pbr"]):.2f}" if meta_row["pbr"] else "",
      "通期実績売上": str(int(sales)) if sales else "",
      "通期実績営業利益率": margin
    }

