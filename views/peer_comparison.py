import pandas as pd
import streamlit as st

from database.load_repository import load_peer_summary
from database.load_repository import load_analysis_data
from services.analysis_loader import prepare_analysis_for_view
from services.analysis_loader import restore_analysis_to_session


def load_json(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value      # Supabase
    return json.loads(value)   # SQLite


def safe_float(x):
    try:
        return float(x)
    except:
        return None


def render_peer_comparison(tic,comp,analysis):
    row_data, meta_row = load_analysis_data(tic)

    ap = analysis["meta"]["annual_performance"] or {}
    history = ap.get("history", {})
    actual_years = sorted(
        [k for k, v in history.items() if v.get("type") == "actual"]
    )

    current_year = history[actual_years[-1]] if actual_years else {}
    previous_year = history[actual_years[-2]] if len(actual_years) >= 2 else {}

    annual_sales = float(current_year.get("revenue") or 0)
    annual_operating_income = float(current_year.get("operating_income") or 0)

    previous_sales = float(previous_year.get("revenue") or 0)

    sales_growth = (
        (annual_sales - previous_sales) / previous_sales * 100
        if previous_sales > 0
        else None
    )
    
    op_margin = (
        annual_operating_income / annual_sales *100
        if annual_sales else None
    )
    if meta_row and meta_row["financial_meta_json"]:
        financial_meta = load_json(meta_row["financial_meta_json"])
    else:
        financial_meta = {} 
    exchange_name = financial_meta.get("exchange_name") if financial_meta else "不明"
    shares_issued = safe_float(analysis["meta"].get("shares_issued")) or 0
    treasury_shares = safe_float(analysis["meta"].get("treasury_shares")) or 0
    ns_shares = shares_issued - treasury_shares
    price = safe_float(meta_row["current_price"]) if meta_row else None
    ap_forecast = analysis["meta"].get("user_forecast",{})
    year1 = ap_forecast.get("year1", {})
    user_fc_net_income = safe_float(year1.get("net_income"))
    user_fc_per = None
    if (
        user_fc_net_income is not None
        and user_fc_net_income > 0
        and ns_shares > 0
        and price is not None
    ):
        user_fc_eps = (user_fc_net_income / ns_shares) * 1000000
        user_fc_per = price / user_fc_eps

    if (
        "peer_comparison_df" not in st.session_state
        or not isinstance(st.session_state.peer_comparison_df, pd.DataFrame)
        or st.session_state.peer_comparison_df.iloc[0]["証券コード"] != tic
    ):
        first_row = {
            "会社名": comp,
            "証券コード": tic,
            "上場区分": exchange_name,
            "PER": round(float(meta_row["per"]), 2) if meta_row and meta_row["per"] is not None else "",
            "独自予想PER": round(float(user_fc_per), 2) if user_fc_per is not None else "",
            "PBR": round(float(meta_row["pbr"]), 2) if meta_row and meta_row["pbr"] is not None else "",
            "通期実績売上": int(annual_sales) if annual_sales else "",
            "売上成長率": f"{sales_growth:.1f}%" if sales_growth is not None else "",
            "通期実績営業利益率": f"{op_margin:.1f}%" if op_margin is not None else ""
        }

        empty_rows =[{
            "会社名": "",
            "証券コード": "",
            "上場区分": "",
            "PER": "",
            "独自予想PER": "",
            "PBR": "",
            "通期実績売上": "",
            "売上成長率": "",
            "通期実績営業利益率": ""
        } for _ in range(5)]

        st.session_state.peer_comparison_df = pd.DataFrame(
            [first_row] + empty_rows
        )

    with st.form(key=f"user_comparison_form_{tic}"):

        edited_df = st.session_state.peer_comparison_df.copy()
        edited_df.iloc[0] = {
        "会社名": comp,
        "証券コード": tic,
        "上場区分": exchange_name,
        "PER": f"{float(meta_row["per"]):.2f}" if meta_row and meta_row["per"] not in (None, "") else "",
        "独自予想PER": (f"{user_fc_per:.2f}" if user_fc_per is not None else ""),
        "PBR": f"{float(meta_row["pbr"]):.2f}" if meta_row and meta_row["pbr"] not in (None, "") else "",
        "通期実績売上": str(int(annual_sales)) if annual_sales else "",
        "売上成長率": f"{sales_growth:.1f}%" if sales_growth is not None else "",
        "通期実績営業利益率": f"{op_margin:.1f}%" if op_margin is not None else ""
        }

        edited_df = st.data_editor(
            edited_df,
            width="stretch",
            num_rows="fixed",
            key="peer_comparison_editor"
        )

        submitted = st.form_submit_button(
            " 💾 同業他社比較を更新",
            width="stretch"
        )

    if submitted:

        for i in range(0, len(edited_df)):
            ticker = str(edited_df.at[i, "証券コード"]).strip()

            if ticker:
                peer = load_peer_summary(ticker)
                if peer is not None:

                    edited_df.at[i, "PER"] = peer["PER"]
                    edited_df.at[i, "PBR"] = peer["PBR"]
                    edited_df.at[i, "独自予想PER"] = peer["独自予想PER"]
                    edited_df.at[i, "会社名"] = peer["会社名"]
                    edited_df.at[i, "上場区分"] = peer["上場区分"]
                    edited_df.at[i, "通期実績売上"] = peer["通期実績売上"]
                    edited_df.at[i, "売上成長率"] = peer["売上成長率"]
                    edited_df.at[i, "通期実績営業利益率"] = peer["通期実績営業利益率"]

        st.session_state.peer_comparison_df = edited_df.copy()
        st.success("同業他社比較表を更新しました")
        st.rerun()


    st.markdown("##### 他社へ移動")
    peer_df = st.session_state.peer_comparison_df
    cols = st.columns(5)
    i = 0
    for _, row in peer_df.iterrows():
        ticker = str(row["証券コード"]).strip()
        company = str(row["会社名"]).strip()
        if not ticker or ticker == tic:
            continue
        with cols[i % 5]:
            if st.button(company, key=f"peer_{ticker}", use_container_width=True):
                st.session_state.selected_ticker = ticker
                st.rerun()
        i += 1
