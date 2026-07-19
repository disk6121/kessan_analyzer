import streamlit as st
import pandas as pd

from views.growth_view import render_growth_table  
from views.growth_view import render_progress_table
from views.stock_view import render_stock_metrics
from views.financial_view import render_financial_metrics
from views.quarter_chart_view import render_quarter_chart
from views.segment_view import render_segment_analysis
from views.kpi_view import render_kpi_editor
from views.sidebar.basic_info import render_basic_info
from views.sidebar.annual_editor import render_annual_editor
from views.sidebar.meta_editor import render_meta_editor
from views.sidebar.quarter_editor import render_quarter_editor
from views.sidebar.segment_editor import render_segment_editor
from views.sidebar.quarter_actual_viewer import render_quarter_actual_viewer
from views.sidebar.segment_viewer import render_segment_viewer
from views.user_forecast import render_user_forecast
from utils.create_segdata_utils import create_segment_dataframe

# ---------------------------------------------------------
# 
# ---------------------------------------------------------


def render_analysis_visuals(stock_meta, combined_data, seg_by_quarter):
    ticker = stock_meta.get("ticker")
    exchange_name = stock_meta.get("exchange_name", "")
    exchange_str = f"（{exchange_name}）" if exchange_name else ""
    df_pivot_rev, df_pivot_prof = create_segment_dataframe(seg_by_quarter)

    st.markdown(
        f"<h2 style='font-size: 28px; font-weight: bold;'>📋 {stock_meta['company_name']}{exchange_str} 決算分析ダッシュボード</h2>", 
        unsafe_allow_html=True
    )

    render_growth_table(stock_meta)

    render_progress_table(stock_meta, combined_data)

    render_user_forecast(stock_meta)
    
    st.divider()
    
    render_stock_metrics(stock_meta)

    st.divider()
    
    render_financial_metrics(stock_meta)
    
    stock_meta = render_kpi_editor(stock_meta, combined_data)

    kpi_data = stock_meta.get("kpi_data", {})
    if kpi_data:
        first_q = next(iter(kpi_data.values()), {})
        kpi_items = list(first_q.keys())
        selected_kpi = st.selectbox(
            "表示するKPI",
            kpi_items
        )
    else:
        selected_kpi = None
    
    render_quarter_chart(combined_data,stock_meta.get("kpi_data",{}),selected_kpi)

    render_segment_analysis(df_pivot_rev, df_pivot_prof)


    with st.sidebar:
        st.header("データの確認・修正")

        
        with st.form(key=f"sidebar_edit_form_{ticker}"):

            render_basic_info(stock_meta)

            render_annual_editor(stock_meta)

            render_meta_editor(stock_meta)

            render_quarter_editor(ticker,combined_data)

            render_segment_editor(ticker,seg_by_quarter)

            submitted = st.form_submit_button(
                "💾 サイドバーの修正内容を反映 ",
                width="stretch"
            )

        if submitted:
            st.success("修正内容を更新しました！")
            st.rerun()
   
        render_quarter_actual_viewer(ticker,combined_data)

        render_segment_viewer(df_pivot_rev, df_pivot_prof)


