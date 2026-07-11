import json
import streamlit as st
import pandas as pd

from database.load_repository import load_analysis_data
from database.supabase_client import supabase


def load_json(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value      # Supabase
    return json.loads(value)   # SQLite

import copy

def convert_annual_performance(annual_perf):
    """
    annual_performanceを新形式へ変換する。
    既に新形式ならそのまま返す。
    """
    if not annual_perf:
        return {"history": {}}

    # 既に新形式
    if "history" in annual_perf:
        return annual_perf
    history = {}

    # 実績
    for key in ["prior_year_actual", "current_year_actual_or_forecast"]:
        item = annual_perf.get(key)
        if item and item.get("fiscal_year"):
            tmp = copy.deepcopy(item)
            tmp["type"] = "actual"
            history[str(item["fiscal_year"])] = tmp

    # 予想
    forecast = annual_perf.get("next_year_forecast")
    if forecast and forecast.get("fiscal_year"):
        tmp = copy.deepcopy(forecast)
        tmp["type"] = "forecast"
        history[str(forecast["fiscal_year"])] = tmp
    history = dict(sorted(history.items(), key=lambda x: int(x[0])))
    return {
        "history": history
    }


def prepare_analysis_for_view(ticker):
    row_data, meta_row= load_analysis_data(ticker)
   
    if row_data and meta_row:

        saved_combined = load_json(row_data["combined_data_json"])
        saved_seg = load_json(row_data["seg_data_json"])
        saved_deep_dive_memo = row_data["deep_dive_memo"]
         
        financial_meta = {}
        if meta_row["financial_meta_json"]:
            financial_meta = load_json(meta_row["financial_meta_json"])
        annual_perf = {}
        if meta_row["annual_perf_json"]:
            annual_perf = load_json(meta_row["annual_perf_json"])
            #annual_perf = convert_annual_performance(annual_perf)
        
        user_forecast = {}
        if meta_row["user_forecast_json"]:
                try:
                    user_forecast = load_json(meta_row["user_forecast_json"])

                    # 古い不正データ対策
                    if isinstance(user_forecast, list):
                        if len(user_forecast) > 0:
                            user_forecast = json.loads(user_forecast[0])
                        else:
                            user_forecast = {}

                except Exception:
                    user_forecast = {}
            
        loaded_exchange = financial_meta.get("exchange_name") if financial_meta else "不明"
        
        peer_comparison_df = None
        if row_data["peer_comparison_json"]:
            peer_comparison_df = pd.DataFrame(load_json(row_data["peer_comparison_json"]))


        saved_meta = {
            "ticker": meta_row["ticker"],
            "company_name": meta_row["company_name"],
            "analyzed_period": meta_row["analyzed_period"],
            "current_price": meta_row["current_price"],
            "exchange_name": loaded_exchange,
            "per": meta_row["per"],
            "pbr": meta_row["pbr"],
            "div_yield": meta_row["div_yield"],
            "cash_and_deposits": financial_meta.get("cash_and_deposits"),
            "interest_bearing_debt": financial_meta.get("interest_bearing_debt"),
            "equity_ratio": financial_meta.get("equity_ratio"),
            "eps_basic": financial_meta.get("eps_basic"),
            "eps_diluted": financial_meta.get("eps_diluted"),
            "annual_performance": annual_perf,
            "user_forecast": user_forecast,
            "net_income_forecast": financial_meta.get("net_income_forecast", 0),
            "net_assets": financial_meta.get("net_assets", 0),
            "non_controlling_interests": financial_meta.get("non_controlling_interests", 0),           
            "dividend_forecast": financial_meta.get("dividend_forecast", 0),
            "shares_issued": financial_meta.get("shares_issued", 0),
            "treasury_shares": financial_meta.get("treasury_shares", 0),
        }
                          
        return {
            "meta": saved_meta,
            "combined": saved_combined,
            "seg": saved_seg,
            "reports": row_data["ai_deep_dive_json"],
            "deep_dive_memo": saved_deep_dive_memo,
            "peer_comparison": peer_comparison_df,
            "user_forecast": saved_meta["user_forecast"]
        }
    




def restore_analysis_to_session(input_ticker,loaded):
    saved_meta = loaded["meta"]
    saved_combined = loaded["combined"]
    saved_seg = loaded["seg"]
    saved_reports = loaded["reports"]
    saved_deep_dive_memo = loaded["deep_dive_memo"]
    saved_user_forecast = loaded["user_forecast"]
    saved_peer_comparison_df = loaded["peer_comparison"]

    if st.session_state.get("last_loaded_ticker") != input_ticker:### 新たなtickerが入力されたことの確認
        st.session_state.last_loaded_ticker = input_ticker

        st.session_state.reports_dict = {}

        if saved_reports:
            if isinstance(saved_reports, dict):
                st.session_state.reports_dict.update(saved_reports)

            elif isinstance(saved_reports, str):
                try:
                    loaded_dict = json.loads(saved_reports)
                    if isinstance(loaded_dict, dict):
                        st.session_state.reports_dict.update(loaded_dict)
                    else:
                        st.session_state.reports_dict["事業概要"] = saved_reports

                except Exception:
                    st.session_state.reports_dict["事業概要"] = saved_reports
         
        if saved_deep_dive_memo:
            st.session_state.deep_dive_memo_input = saved_deep_dive_memo
        else:
            st.session_state.deep_dive_memo_input = ""
        
        if saved_peer_comparison_df is not None:
            st.session_state.peer_comparison_df = saved_peer_comparison_df
        else:
            st.session_state.peer_comparison_df = ""


        saved_meta["user_forecast"] = saved_user_forecast

        st.session_state.current_analysis = {
            "meta": saved_meta, "combined": saved_combined, "seg": saved_seg, "ai_report": None, "source":"db"
        }



def load_saved_reports_to_session(ticker):
    """
    Supabaseに保存されているAI深掘り結果だけをSessionへ復元する
    （新規PDF解析時に使用）
    """

    st.session_state.reports_dict = {}

    result = (
        supabase
        .table("initial_data")
        .select("ai_deep_dive_json")
        .eq("ticker", ticker)
        .execute()
    )

    if not result.data:
        return

    reports = result.data[0].get("ai_deep_dive_json")

    if reports is None:
        return

    if isinstance(reports, dict):
        st.session_state.reports_dict = reports.copy()

    elif isinstance(reports, str):
        try:
            loaded = json.loads(reports)

            if isinstance(loaded, dict):
                st.session_state.reports_dict = loaded
            else:
                st.session_state.reports_dict = {
                    "事業概要": reports
                }

        except Exception:
            st.session_state.reports_dict = {
                "事業概要": reports
            }
