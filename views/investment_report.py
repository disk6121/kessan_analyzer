
import streamlit as st


def render_analysis_section(icon, section):
    if not section:
        return

    st.subheader(f"{icon} {section.get('title','')}")
    comment = section.get("comment","")
    if comment:
        st.info(comment)
    positive = section.get("positive_points", [])
    if positive:
        st.success("✅ 強み")
        for item in positive:
            st.write(f"• {item}")
    concerns = section.get("concerns", [])
    if concerns:
        st.warning("⚠️ 懸念点")
        for item in concerns:
            st.write(f"• {item}")
    growth = section.get("growth_drivers", [])
    if growth:
        st.info("🚀 成長ドライバー")
        for item in growth:
            st.write(f"• {item}")
    watch = section.get("watch_points", [])
    if watch:
        st.info("👀 注目ポイント")
        for item in watch:
            st.write(f"• {item}")


def render_investment_report(report):

    if not report:
        return

    st.divider()
    st.header("🤖 AI投資判断レポート")
    view = report.get("investment_view", {})
    stance = view.get("stance","")
    reason = view.get("reason","")
    color_map = {
        "非常に注目":"🟢",
        "注目":"🟢",
        "中立":"🟡",
        "慎重":"🟠",
        "非常に慎重":"🔴"
    }
    icon = color_map.get(stance,"⚪")
    st.subheader(f"{icon} 投資スタンス：{stance}")

    st.info(reason)
    render_analysis_section("📈", report.get("growth"))
    render_analysis_section("📊", report.get("profitability"))
    render_analysis_section("🏦", report.get("financial_health"))
    render_analysis_section("💰", report.get("valuation"))
    scenario = report.get("investment_scenario", {})

    st.divider()
    st.subheader("📌 投資シナリオ")
    st.write("#### 📈 Bullケース")
    st.success(scenario.get("bull_case",""))
    st.write("")
    st.write("#### 📉 Bearケース")
    st.warning(scenario.get("bear_case",""))

    kpi = scenario.get("key_monitoring_points", [])
    if kpi:
        st.write("")
        st.write("#### 👀 継続的に確認したい指標")
        for item in kpi:
            st.write(f"• {item}")

    risks = report.get("investment_risks", {})
    st.divider()
    st.subheader("⚠️ 投資リスク")

    business = risks.get("business_risks", [])
    if business:
        st.write("#### 事業リスク")
        for item in business:
            st.write(f"• {item}")

    financial = risks.get("financial_risks", [])
    if financial:
        st.write("#### 財務リスク")
        for item in financial:
            st.write(f"• {item}")

    market = risks.get("market_risks", [])
    if market:
        st.write("#### 市場リスク")
        for item in market:
            st.write(f"• {item}")

    st.divider()
    st.subheader("👀 次回決算で注目すべきポイント")
    focus = report.get("next_quarter_focus", [])
    for i,item in enumerate(focus,1):
        st.write(f"{i}. {item}")

    st.divider()
    st.subheader("📝 総括")
    st.success(report.get("summary",""))

