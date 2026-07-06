
import streamlit as st
import pandas as pd


def update_user_forecast(stock_meta, edited_df, forecast_memo):

    if edited_df is None:
        return

    metrics_map = {
        "売上高": "revenue",
        "売上総利益": "gross_profit",
        "営業利益": "operating_income",
        "経常利益": "ordinary_income",
        "純利益": "net_income"
    }

    user_forecast = {
        "year1": {},
        "year2": {},
        "memo": forecast_memo
    }

    for _, row in edited_df.iterrows():

        metric = metrics_map[row["項目"]]

        v1 = row["独自予想(1期目)"]
        v2 = row["独自予想(2期目)"]

        user_forecast["year1"][metric] = (
        None if pd.isna(v1) else float(v1 or 0)
        )

        user_forecast["year2"][metric] = (
        None if pd.isna(v2) else float(v2 or 0)
        )

    stock_meta["user_forecast"] = user_forecast
    if "current_analysis" in st.session_state:
        st.session_state.current_analysis["meta"]["user_forecast"] = user_forecast
