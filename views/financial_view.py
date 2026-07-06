import streamlit as st

stock_meta = {"ticker": None, "company_name": None, "analyzed_period": "不明", "annual_performance": {}}

# ---------------------------------------------------------
# 財務データ欄
# ---------------------------------------------------------

def render_financial_metrics(stock_meta):
    st.write("#### 🔹 財務健全性データ")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    cash, debt, ratio = stock_meta.get("cash_and_deposits"), stock_meta.get("interest_bearing_debt"), stock_meta.get("equity_ratio")
    col_f1.metric("現預金", f"{cash:,.0f} 百万円" if cash else "データなし")
    col_f2.metric("有利子負債", f"{debt:,.0f} 百万円" if debt else "データなし")
    col_f3.metric("ネットキャッシュ", f"{cash - debt:,.0f} 百万円" if cash is not None and debt is not None else "算出不可")
    col_f4.metric("自己資本比率", f"{ratio:.2f} %" if ratio else "データなし")

