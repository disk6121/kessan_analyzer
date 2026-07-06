
import streamlit as st
import pandas as pd


def render_annual_editor(stock_meta):

    with st.expander("⚙️ 通期業績推移と翌期予想"):

        ticker = stock_meta.get("ticker")
        ap = stock_meta.get("annual_performance", {}) or {}
        p_actual = ap.get("prior_year_actual") or {}
        c_actual = ap.get("current_year_actual_or_forecast") or {}
        n_forecast = ap.get("next_year_forecast") or {}

        # エディタに渡すための初期DataFrameを作成
        annual_df_input = pd.DataFrame({
            "項目": ["売上高 (百万円)","売上総利益 (百万円)", "営業利益 (百万円)", "経常利益 (百万円)", "純利益 (百万円)"],
            "２期前通期実績": [
                float(p_actual.get("revenue") or 0),
                float(p_actual.get("gross_profit") or 0),
                float(p_actual.get("operating_income") or 0),
                float(p_actual.get("ordinary_income") or 0),
                float(p_actual.get("net_income") or 0)
            ],
            "直近期通期実績": [
                float(c_actual.get("revenue") or 0),
                float(c_actual.get("gross_profit") or 0),
                float(c_actual.get("operating_income") or 0),
                float(c_actual.get("ordinary_income") or 0),
                float(c_actual.get("net_income") or 0)
            ],
            "次期通期予想": [
                float(n_forecast.get("revenue") or 0),
                float(n_forecast.get("gross_profit") or 0),
                float(n_forecast.get("operating_income") or 0),
                float(n_forecast.get("ordinary_income") or 0),
                float(n_forecast.get("net_income") or 0)
            ]
        })

        # データエディタの配置（数値のみユーザーに変更してもらう）
        edited_annual_df = st.data_editor(
            annual_df_input,
            use_container_width=True,
            hide_index=True,
            disabled=["項目"], # 項目名は編集不可
            key=f"annual_perf_editor_{ticker}"
        )

        # 💡 【リアルタイム上書き＆再計算用データの準備】
        if edited_annual_df is not None:
            # ユーザーが編集した値を元の構造に書き戻す
            for period_idx, period_key in enumerate(["prior_year_actual", "current_year_actual_or_forecast", "next_year_forecast"]):
                if period_key not in ap:
                    ap[period_key] = {}
                col_name = ["２期前通期実績", "直近期通期実績", "次期通期予想"][period_idx]
            
                ap[period_key]["revenue"] = float(edited_annual_df.loc[0, col_name])
                ap[period_key]["gross_profit"] = float(edited_annual_df.loc[1, col_name])
                ap[period_key]["operating_income"] = float(edited_annual_df.loc[2, col_name])
                ap[period_key]["ordinary_income"] = float(edited_annual_df.loc[3, col_name])
                ap[period_key]["net_income"] = float(edited_annual_df.loc[4, col_name])

        