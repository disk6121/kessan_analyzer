import streamlit as st


# ---------------------------------------------------------
# 📈 株価分析欄 
# ---------------------------------------------------------
def safe_float(x):
    try:
        return float(x)
    except:
        return None

def render_stock_metrics(stock_meta):
    st.write("#### 📈 株価分析データ")
    col_p1, col_p2, col_p3, col_p4, col_p5, col_p6 = st.columns(6)
    col_p7, col_p8, col_p9, col_p10, col_p11 = st.columns(5)
    price = safe_float(stock_meta.get("current_price"))
    eps_basic = stock_meta.get("eps_basic")
    eps_diluted = stock_meta.get("eps_diluted")
    per_forward = safe_float(stock_meta.get("per") )
    pbr = safe_float(stock_meta.get("pbr"))
    div_yield = safe_float(stock_meta.get("div_yield"))
    shares_issued = safe_float(stock_meta.get("shares_issued", 0) or 0)
    treasury_shares = safe_float(stock_meta.get("treasury_shares", 0) or 0)
    ns_shares = shares_issued - treasury_shares
    if price and ns_shares > 0:
        market_cap_okuen = (price * ns_shares) / 100000000
    else:
        market_cap_okuen = None
    dilution_rate = None
    if (
        eps_basic is not None
        and eps_diluted is not None
        and eps_basic > 0
    ):
        dilution_rate = eps_diluted / eps_basic * 100

    user_fc = stock_meta.get("user_forecast", {})
    year1 = user_fc.get("year1", {})
    year2 = user_fc.get("year2", {})
    
    # ROE
    net_assets = safe_float(stock_meta.get("net_assets", 0) or 0)
    net_income_forecast = safe_float(stock_meta.get("net_income_forecast", 0) or 0)

    roe = None
    if net_assets > 0:
        roe = net_income_forecast / net_assets * 100

    # 独自予想1期目・2期目の純利益
    year1_net_income = safe_float(year1.get("net_income"))
    year2_net_income = safe_float(year2.get("net_income"))

    # 独自予想PER
    per_year1 = None
    per_year2 = None
    eps1 = None
    eps2 = None

    if (
        year1_net_income is not None
        and year1_net_income > 0
        and ns_shares > 0
    ):
        eps1 = (year1_net_income / ns_shares) * 1000000
        per_year1 = price / eps1

    if (
        year2_net_income is not None
        and year2_net_income > 0
        and ns_shares > 0
    ):
        eps2 = (year2_net_income / ns_shares) * 1000000
        per_year2 = price / eps2

    col_p1.metric("株価", f"{price:,.1f} 円" if price else "データなし")
    col_p2.metric("時価総額", f"{market_cap_okuen:,.0f} 億円" if market_cap_okuen else "データなし")
    col_p3.metric("PER (予想)", f"{per_forward:.2f} 倍" if per_forward else "データなし")
    col_p4.metric("PBR (実績)", f"{pbr:.2f} 倍" if pbr else "データなし")
    col_p5.metric("配当利回り (予想)", f"{div_yield:.2f} %" if div_yield else "データなし")
    col_p6.metric("希薄化率",  f"{dilution_rate:.1f} %" if dilution_rate is not None else "データなし")
    col_p7.metric("ROE (予想)", f"{roe:.2f} %" if roe is not None else "データなし")
    col_p8.metric("PER (独自予想１期目)", f"{per_year1:.2f} 倍" if per_year1 is not None else "データなし")
    col_p9.metric("EPS(独自予想１期目)", f"{eps1:.1f}" if eps1 is not None else "データなし")
    col_p10.metric("PER (独自予想２期目)", f"{per_year2:.2f} 倍" if per_year2 is not None else "データなし")
    col_p11.metric("EPS(独自予想２期目)", f"{eps2:.1f}" if eps2 is not None else "データなし")