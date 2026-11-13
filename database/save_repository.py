
from database.supabase_client import supabase

import json
import streamlit as st
import math
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo

def prepare_analysis_data(
        analysis,
        reports_dict,
        deep_dive_memo,
        peer_comparison_df
):

    meta = analysis["meta"]
    today_str = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d")

    financial_pack = {
        "exchange_name":meta.get("exchange_name"),
        "cash_and_deposits": meta.get("cash_and_deposits"),
        "interest_bearing_debt": meta.get("interest_bearing_debt"),
        "equity_ratio": meta.get("equity_ratio"),
        "shares_issued": meta.get("shares_issued"),
        "treasury_shares": meta.get("treasury_shares"),
        "net_income_forecast": meta.get("net_income_forecast"),
        "net_assets": meta.get("net_assets"),
        "non_controlling_interests": meta.get("non_controlling_interests"),
        "dividend_forecast": meta.get("dividend_forecast"),
        "eps_basic": meta.get("eps_basic"),
        "eps_diluted": meta.get("eps_diluted")
    }
    annual_perf_pack = meta.get("annual_performance", {})
    kpi_pack = replace_nan(meta.get("kpi_data", {}))
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
        "kpi_pack": kpi_pack,
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

def calculate_assumed_eps(financial_pack, user_forecast):
    """
    独自予想1期目の純利益から想定EPSを計算する。

    純利益：百万円
    発行済株式数・自己株式数：株
    """

    try:
        shares_issued = float(
            financial_pack.get("shares_issued") or 0
        )

        treasury_shares = float(
            financial_pack.get("treasury_shares") or 0
        )

        net_shares = shares_issued - treasury_shares

        year1 = user_forecast.get("year1", {})
        net_income = year1.get("net_income")

        if net_income is None:
            return None

        net_income = float(net_income)

        if not math.isfinite(net_income):
            return None

        if not math.isfinite(net_shares) or net_shares <= 0:
            return None

        eps = net_income * 1_000_000 / net_shares

        if not math.isfinite(eps):
            return None

        return eps

    except (TypeError, ValueError, AttributeError):
        return None


def save_company(prepared):

    meta = prepared["meta"]

    # -----------------------------------------------------
    # 既存データを取得
    # -----------------------------------------------------
    result = (
        supabase.table("companies")
        .select(
            """
            buy_target,
            sell_target,
            investment_memo,
            is_favorite,
            is_short_term,
            evaluation,
            assumed_per
            """
        )
        .eq("ticker", meta["ticker"])
        .execute()
    )

    if result.data:
        row = result.data[0]

        buy_target = row.get("buy_target")
        sell_target = row.get("sell_target")
        investment_memo = row.get("investment_memo") or ""

        is_favorite = row.get("is_favorite")
        is_short_term = row.get("is_short_term")

        evaluation = row.get("evaluation")
        assumed_per = row.get("assumed_per")

    else:
        buy_target = None
        sell_target = None
        investment_memo = ""

        is_favorite = False
        is_short_term = False

        evaluation = None
        assumed_per = None

    # -----------------------------------------------------
    # JSONデータの整理
    # -----------------------------------------------------
    financial_pack = replace_nan(
        prepared["financial_pack"]
    )

    user_forecast_json = replace_nan(
        meta.get("user_forecast", {})
    )

    # -----------------------------------------------------
    # 独自予想EPSを計算
    # -----------------------------------------------------
    assumed_eps = calculate_assumed_eps(
        financial_pack,
        user_forecast_json
    )

    # -----------------------------------------------------
    # 保存日時
    # -----------------------------------------------------
    saved_at = datetime.now(
        ZoneInfo("Asia/Tokyo")
    )

    # -----------------------------------------------------
    # companiesテーブルへ保存
    # -----------------------------------------------------
    (
        supabase.table("companies")
        .upsert(
            {
                "ticker": meta["ticker"],
                "company_name": meta["company_name"],
                "analyzed_period": meta["analyzed_period"],
                "saved_date": saved_at.isoformat(),

                "current_price": meta.get("current_price"),
                "per": meta.get("per"),
                "pbr": meta.get("pbr"),
                "div_yield": meta.get("div_yield"),

                "is_favorite": is_favorite,
                "is_short_term": is_short_term,

                "investment_memo": investment_memo,

                "evaluation": evaluation,
                "assumed_per": assumed_per,
                "assumed_eps": assumed_eps,

                "financial_meta_json": financial_pack,
                "annual_perf_json": prepared["annual_perf_pack"],
                "kpi_json": prepared["kpi_pack"],

                "buy_target": buy_target,
                "sell_target": sell_target,

                "user_forecast_json": user_forecast_json
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



def save_companies_memo_pre(edited_df):
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

def save_companies_memo(edited_df):

    for _, row in edited_df.iterrows():

        ticker = str(row["証券コード"]).strip().upper()

        assumed_per = pd.to_numeric(
            pd.Series([row["想定PER"]]),
            errors="coerce"
        ).iloc[0]

        evaluation = row["評価"]
        investment_memo = row["投資メモ"]

        data = {
            "is_favorite": bool(row["長期投資候補"]),
            "is_short_term": bool(row["短期投資候補"]),
            "evaluation": (
                None if pd.isna(evaluation)
                else str(evaluation)
            ),
            "assumed_per": (
                None if pd.isna(assumed_per)
                else float(assumed_per)
            ),
            "investment_memo": (
                None if pd.isna(investment_memo)
                else str(investment_memo)
            )
        }

        supabase.table("companies").update(
            data
        ).eq(
            "ticker", ticker
        ).execute()

def save_common_note(note):
    (
        supabase
        .table("app_settings")
        .upsert({
            "setting_key": "common_note",
            "setting_value": note
        })
        .execute()
    )



def update_stock_metrics(
    ticker,
    current_price,
    per,
    pbr,
    div_yield
):
    """
    companiesテーブルの株価関連指標だけを更新する。
    """

    try:
        (
            supabase.table("companies")
            .update({
                "current_price": current_price,
                "per": per,
                "pbr": pbr,
                "div_yield": div_yield,
            })
            .eq("ticker", ticker)
            .execute()
        )

        return True

    except Exception as e:
        st.error(f"株価指標の保存に失敗しました: {e}")
        return False
