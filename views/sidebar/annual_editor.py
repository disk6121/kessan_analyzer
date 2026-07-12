
import streamlit as st
import pandas as pd


def render_annual_editor_past(stock_meta):

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
            format="%,.0f",
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


def render_annual_editor(stock_meta):

    with st.expander("⚙️ 通期業績推移と翌期予想"):

        ticker = stock_meta.get("ticker")

        ap = stock_meta.get("annual_performance", {}) or {}

        history = ap.get("history", {})

        # -------------------------
        # DataFrame作成
        # -------------------------
        rows = []

        for year in sorted(history.keys(), key=int):

            data = history[year]

            rows.append({
                "年度": int(year),
                "区分": "予想" if data.get("type") == "forecast" else "実績",
                "売上高": float(data.get("revenue") or 0),
                "売上総利益": float(data.get("gross_profit") or 0),
                "営業利益": float(data.get("operating_income") or 0),
                "経常利益": float(data.get("ordinary_income") or 0),
                "純利益": float(data.get("net_income") or 0),
            })

        annual_df_input = pd.DataFrame(rows)

        # -------------------------
        # DataEditor
        # -------------------------
        edited_annual_df = st.data_editor(
            annual_df_input,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=f"annual_perf_editor_{ticker}",
            column_config={
                "年度": st.column_config.NumberColumn(
                    "年度",
                    step=1,
                    format="%d",
                ),
                "区分": st.column_config.SelectboxColumn(
                    "区分",
                    options=["実績", "予想"],
                    required=True,
                ),
                "売上高": st.column_config.NumberColumn("売上高"),
                "売上総利益": st.column_config.NumberColumn("売上総利益"),
                "営業利益": st.column_config.NumberColumn("営業利益"),
                "経常利益": st.column_config.NumberColumn("経常利益"),
                "純利益": st.column_config.NumberColumn("純利益"),
            },
        )

        # -------------------------
        # historyへ戻す
        # -------------------------
        if edited_annual_df is not None:

            history = {}

            for _, row in edited_annual_df.iterrows():

                if pd.isna(row["年度"]):
                    continue

                year = str(int(row["年度"]))

                history[year] = {
                    "fiscal_year": int(row["年度"]),
                    "type": (
                        "forecast"
                        if row["区分"] == "予想"
                        else "actual"
                    ),
                    "revenue": float(row["売上高"] or 0),
                    "gross_profit": float(row["売上総利益"] or 0),
                    "operating_income": float(row["営業利益"] or 0),
                    "ordinary_income": float(row["経常利益"] or 0),
                    "net_income": float(row["純利益"] or 0),
                }

            # -------------------------
            # 年度順に並べ替え
            # -------------------------
            history = dict(
                sorted(
                    history.items(),
                    key=lambda x: int(x[0])
                )
            )

            # -------------------------
            # 予想は最新年度だけ残す
            # -------------------------
            forecast_years = [
                int(y)
                for y, d in history.items()
                if d.get("type") == "forecast"
            ]

            if len(forecast_years) > 1:

                newest = max(forecast_years)

                for y in history:

                    if (
                        history[y]["type"] == "forecast"
                        and int(y) != newest
                    ):
                        history[y]["type"] = "actual"

            ap["history"] = history


