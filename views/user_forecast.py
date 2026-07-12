
import streamlit as st
import pandas as pd

from services.forecast_service import update_user_forecast

def render_user_forecast(stock_meta):

    ticker = stock_meta["ticker"]
    user_fc = stock_meta.get("user_forecast",{})

    st.write("#### ✏️ 独自予想")

    if not isinstance(user_fc, dict):
        user_fc = {}

    year1 = user_fc.get("year1", {})
    year2 = user_fc.get("year2", {})

    rows = [
        {
            "項目": "売上高",
            "独自予想(1期目)": year1.get("revenue"),
            "独自予想(2期目)": year2.get("revenue")
        },
        {
            "項目": "売上総利益",
            "独自予想(1期目)": year1.get("gross_profit"),
            "独自予想(2期目)": year2.get("gross_profit")
        },
        {
            "項目": "営業利益",
            "独自予想(1期目)": year1.get("operating_income"),
            "独自予想(2期目)": year2.get("operating_income")
        },
        {
            "項目": "経常利益",
            "独自予想(1期目)": year1.get("ordinary_income"),
            "独自予想(2期目)": year2.get("ordinary_income")
        },
        {
            "項目": "純利益",
            "独自予想(1期目)": year1.get("net_income"),
            "独自予想(2期目)": year2.get("net_income")
        }
    ]

    forecast_df = pd.DataFrame(rows)

    with st.form(key=f"user_forecast_form_{ticker}"):
   
        col1, col2 = st.columns([4, 6])

        with col1:
            st.write("✏️ 独自収支予想")
            edited_df = st.data_editor(
                forecast_df,
                hide_index=True,
                width="stretch",
                key=f"user_forecast_editor_{ticker}"
            )

        with col2:
            memo = st.text_area(
                "✏️ 独自予想の根拠",
                value=user_fc.get("memo", ""),
                height=260,
                key=f"user_forecast_memo_{ticker}"
            )

        submitted = st.form_submit_button(
            " 💾 独自予想を更新",
            width="stretch"
        )

    if submitted:
        update_user_forecast(stock_meta,edited_df,memo)
        st.success("独自予想を更新しました")
