import streamlit as st
import json
import pandas as pd

from database.load_repository import load_existing_quarter_data
from services.pdf_analyzer import analyze_pdfs

import copy


def merge_annual_performance(old_perf, new_perf):

    history = {}

    # -----------------------------
    # ① 旧データ読込
    # -----------------------------
    if old_perf:
        # 新形式
        if "history" in old_perf:
            history = copy.deepcopy(old_perf["history"])
        # 旧形式
        else:
            for key in [
                "prior_year_actual",
                "current_year_actual_or_forecast"
            ]:
                item = old_perf.get(key)
                if item and item.get("fiscal_year"):
                    y = str(item["fiscal_year"])
                    tmp = copy.deepcopy(item)
                    tmp["type"] = "actual"
                    history[y] = tmp
            forecast = old_perf.get("next_year_forecast")
            if forecast and forecast.get("fiscal_year"):
                y = str(forecast["fiscal_year"])
                tmp = copy.deepcopy(forecast)
                tmp["type"] = "forecast"
                history[y] = tmp

    # -----------------------------
    # ② 今回解析した実績
    # -----------------------------
    if new_perf:
        current = new_perf.get("current_year_actual_or_forecast")
        if current and current.get("fiscal_year"):
            y = str(current["fiscal_year"])
            tmp = copy.deepcopy(current)
            tmp["type"] = "actual"
            history[y] = tmp

        # -------------------------
        # ③ 来期予想
        # -------------------------
        forecast = new_perf.get("next_year_forecast")
        if forecast and forecast.get("fiscal_year"):
            y = str(forecast["fiscal_year"])
            tmp = copy.deepcopy(forecast)
            tmp["type"] = "forecast"
            history[y] = tmp

    # -----------------------------
    # ④ forecastが取得できなかったら
    #    古いforecastを残す
    # -----------------------------
    forecast_exist = any(
        v.get("type") == "forecast"
        for v in history.values()
    )
    if not forecast_exist and old_perf:
        old_forecast = None
        # 新形式
        if "history" in old_perf:
            for item in old_perf["history"].values():
                if item.get("type") == "forecast":
                    old_forecast = copy.deepcopy(item)
                    break
        # 旧形式
        else:
            old_forecast = old_perf.get("next_year_forecast")
            if old_forecast:
                old_forecast = copy.deepcopy(old_forecast)
                old_forecast["type"] = "forecast"
        if old_forecast and old_forecast.get("fiscal_year"):
            y = str(old_forecast["fiscal_year"])
            history[y] = old_forecast

    # -----------------------------
    # ⑤ forecastは1件だけにする
    # -----------------------------
    forecasts = [
        int(y)
        for y, d in history.items()
        if d.get("type") == "forecast"
    ]
    if len(forecasts) >= 2:
        newest = max(forecasts)
        for y in list(history.keys()):
            if (
                history[y].get("type") == "forecast"
                and int(y) != newest
            ):
                history[y]["type"] = "actual"
    history = dict(
        sorted(
            history.items(),
            key=lambda x: int(x[0])
        )
    )
    return {
        "history": history
    }



def manage_analysis(uploaded_files,api_key):
    if not api_key:
        st.error("APIキーが設定されていません。")
    else:
        st.session_state.current_analysis = None
        st.session_state.reports_dict = {}
        st.session_state.last_loaded_ticker = None
        if "deep_dive_memo" in st.session_state:
            st.session_state.deep_dive_memo_input = ""
         
        analysis = analyze_pdfs(uploaded_files,api_key)
        analysis["source"] ="pdf"

        ticker = analysis["meta"]["ticker"]

        old_data = load_existing_quarter_data(ticker)

        if old_data:

            # ---------- 四半期データ統合 ----------
            merged_combined = old_data["combined"]
            merged_combined.update(analysis["combined"])

            merged_seg = old_data["seg"]
            merged_seg.update(analysis["seg"])

            analysis["combined"] = merged_combined
            analysis["seg"] = merged_seg

            # ---------- AI調査結果復元 ----------
            st.session_state.reports_dict = {}

            if old_data["reports"]:
                try:
                    loaded_dict = json.loads(old_data["reports"])

                    if isinstance(loaded_dict, dict):
                        st.session_state.reports_dict.update(loaded_dict)

                except:
                    pass

            # ---------- メモ復元 ----------
            st.session_state.deep_dive_memo_input = (
                old_data["deep_dive_memo"] or ""
            )

            # ------ 同業他社比較表復元 ------
            peer_comparison_json = json.loads(old_data.get("peer_comparison_json","[]"))
            if peer_comparison_json:
                st.session_state.peer_comparison_df = pd.DataFrame(peer_comparison_json)

            # -- 通期決算・通期予想 --
            analyze_period = analysis["meta"].get("analyzed_period", "")
            if any(q in analyze_period for q in ["1Q", "2Q", "3Q"]):
                old_annual_performance = (old_data["annual_perf"])
                    if old_annual_performance:
                        analysis["meta"]["annual_performance"] = old_annual_performance
            
            #old_annual_performance = old_data["annual_perf"]
            #if any(q in analyze_period for q in ["1Q", "2Q", "3Q"]):
                # 1～3Qは通期データを更新しない
            #    if old_annual_performance:
            #        analysis["meta"]["annual_performance"] = old_annual_performance
            #else:
                # 4Qは履歴を残して更新
            #    analysis["meta"]["annual_performance"] = merge_annual_performance(
            #        old_annual_performance,
            #        analysis["meta"]["annual_performance"]
            #    )
            
            # ------ 独自予想復元 ------
            old_user_forecast = (old_data["user_forecast"])
            if old_user_forecast:
                analysis["meta"]["user_forecast"] = old_user_forecast

        else:
            st.session_state.reports_dict = {}
            st.session_state.deep_dive_memo_input = ""

    return analysis


