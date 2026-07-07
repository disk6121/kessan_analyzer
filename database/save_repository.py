from database.db import get_connection
from database.supabase_client import supabase

import json
import datetime
import streamlit as st
import math
import pandas as pd


def prepare_analysis_data(
        analysis,
        reports_dict,
        deep_dive_memo,
        peer_comparison_df
):

    meta = analysis["meta"]
    today_str = datetime.date.today().strftime("%Y/%m/%d")

    financial_pack = {
        "exchange_name":meta.get("exchange_name"),
        "cash_and_deposits": meta.get("cash_and_deposits"),
        "interest_bearing_debt": meta.get("interest_bearing_debt"),
        "equity_ratio": meta.get("equity_ratio"),
        "shares_issued": meta.get("shares_issued"),
        "treasury_shares": meta.get("treasury_shares"),
        "net_income_forecast": meta.get("net_income_forecast"),
        "net_assets": meta.get("net_assets"),
        "dividend_forecast": meta.get("dividend_forecast"),
        "eps_basic": meta.get("eps_basic"),
        "eps_diluted": meta.get("eps_diluted")
    }
    annual_perf_pack = meta.get("annual_performance", {})
    reports_json_str = json.dumps(reports_dict, ensure_ascii=False)
    peer_comparison_json = (
        st.session_state.peer_comparison_df.to_json(
            orient="records",
            force_ascii=False
        )
        if peer_comparison_df is not None
        else None
    )

    return {
        "meta": meta,
        "today_str": today_str,
        "financial_pack": financial_pack,
        "annual_perf_pack": annual_perf_pack,
        "reports_json_str": reports_json_str,
        "peer_comparison_json": peer_comparison_json,
        "deep_dive_memo": deep_dive_memo
    }


def replace_nan(obj):
    if isinstance(obj, dict):
        return {k: replace_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan(v) for v in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    else:
        return obj


def clean(v):
    if pd.isna(v):
        return None
    return v 



def save_company(prepared):
    meta = prepared["meta"]

    result = (
        supabase.table("companies")
        .select("buy_target, sell_target, investment_memo, is_favorite")
        .eq("ticker", meta["ticker"])
        .execute()
    )

    if result.data:
        row = result.data[0]
        buy_target = row.get("buy_target")
        sell_target = row.get("sell_target")
        investment_memo = row.get("investment_memo")
        is_favorite = row.get("is_favorite")
    else:
        buy_target = None
        sell_target = None
        investment_memo = ""
        is_favorite = False

    financial_pack = replace_nan(prepared["financial_pack"])
    user_forecast_json = replace_nan(meta.get("user_forecast",{}))

    (
        supabase.table("companies")
        .upsert(
            {
                "ticker" : meta["ticker"],
                "company_name" : meta["company_name"],
                "analyzed_period" : meta["analyzed_period"],
                "saved_date" : prepared["today_str"],
                "current_price" : meta.get("current_price"),
                "per" : meta.get("per"),
                "pbr" : meta.get("pbr"),
                "div_yield" : meta.get("div_yield"),
                "is_favorite" : is_favorite,
                "investment_memo" : investment_memo,
                "financial_meta_json" : financial_pack,
                "annual_perf_json" : prepared["annual_perf_pack"],
                "buy_target" : buy_target,
                "sell_target" : sell_target,
                "user_forecast_json" : user_forecast_json
            }
        )
        .execute()
    )


def save_initial_data(analysis, prepared):
    meta = prepared["meta"]

    # 既存データ取得
    result = (
        supabase
        .table("initial_data")
        .select("combined_data_json, seg_data_json")
        .eq("ticker", meta["ticker"])
        .execute()
    )

    if result.data:
        existing = result.data[0]

        old_combined = existing.get("combined_data_json") or {}
        old_seg = existing.get("seg_data_json") or {}

        if isinstance(old_combined, str):
            old_combined = json.loads(old_combined)

        if isinstance(old_seg, str):
            old_seg = json.loads(old_seg)

        old_combined.update(analysis["combined"])
        old_seg.update(analysis["seg"])

        final_combined = old_combined
        final_seg = old_seg

    else:
        final_combined = analysis["combined"]
        final_seg = analysis["seg"]

    (
        supabase
        .table("initial_data")
        .upsert({
            "ticker": meta["ticker"],
            "combined_data_json": final_combined,
            "seg_data_json": final_seg,
            "ai_deep_dive_json": json.loads(prepared["reports_json_str"]),
            "deep_dive_memo": prepared["deep_dive_memo"],
            "peer_comparison_json": prepared["peer_comparison_json"]
        })
        .execute()
    )



def save_analysis_data(
        analysis,
        reports_dict,
        deep_dive_memo,
        peer_comparison_df
):

    prepared = prepare_analysis_data(
        analysis,
        reports_dict,
        deep_dive_memo,
        peer_comparison_df
    )

    save_company(prepared)

    save_initial_data(analysis, prepared)



def save_companies_memo(edited_df):
    for _, row in edited_df.iterrows():
        fav_val = bool(row["⭐お気に入り"])
        (
            supabase
            .table("companies")
            .update({
                "is_favorite": fav_val,
                "investment_memo": clean(row["投資メモ"]),
                "buy_target": clean(row["買いたい価格"]),
                "sell_target": clean(row["売りたい価格"])
            })
            .eq("ticker", row["証券コード"])
            .execute()
        )


def save_common_note(note):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO app_settings(setting_key, setting_value)
        VALUES('common_note', ?)
        ON CONFLICT(setting_key)
        DO UPDATE SET
            setting_value=excluded.setting_value
    """, (note,))
    conn.commit()
    conn.close()


