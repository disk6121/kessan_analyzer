import streamlit as st
import json
import pandas as pd

from database.load_repository import load_existing_quarter_data
from services.pdf_analyzer import analyze_pdfs


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

            # -- 通期決算・通期予想は4Qのときのみ更新 --
            analyze_period = analysis["meta"].get("analyzed_period","")
            if any(q in analyze_period for q in ["1Q", "2Q", "3Q"]):
                old_annual_performance = (old_data["annual_perf"])
                if old_annual_performance:
                    analysis["meta"]["annual_performance"] = old_annual_performance
            
            # ------ 独自予想復元 ------
            old_user_forecast = (old_data["user_forecast"])
            if old_user_forecast:
                analysis["meta"]["user_forecast"] = old_user_forecast

        else:
            st.session_state.reports_dict = {}
            st.session_state.deep_dive_memo_input = ""

    return analysis


