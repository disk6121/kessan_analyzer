import pandas as pd
import streamlit as st
import re


def format_amount(value):
    if value is None:
        return "-"
    return f"{value:,.0f} 百万円"


def get_margin(value, revenue):
    if value is None or revenue is None or revenue == 0:
        return "-"
    return f"{value / revenue * 100:.1f}%"


def get_pct_string(current, base):
    if current is None or base is None or base == 0:
        return "-"
    change = (current - base) / base * 100
    return f"{change:+.1f}%"


def render_growth_table_past(stock_meta):

    st.write("#### 📈 通期実績・通期予想")

    ap = stock_meta.get("annual_performance", {})  or {}
    prior = ap.get("prior_year_actual", {}) or {}
    current = ap.get("current_year_actual_or_forecast", {}) or {}
    next_ = ap.get("next_year_forecast", {}) or {}

    prior_year = prior.get("fiscal_year") 
    current_year = current.get("fiscal_year") 
    next_year = next_.get("fiscal_year") 

    fiscal_month = stock_meta.get("analyzed_period") 
    match = re.search(r"(\d+)月期", str(fiscal_month))
    if match:
        fiscal_month = int(match.group(1))
    else:
        fiscal_month = None

    if next_year is not None:
        current_year = next_year - 1
        prior_year = next_year - 2

    items = [
        ("売上高", "revenue"),
        ("売上総利益", "gross_profit"),
        ("営業利益", "operating_income"),
        ("経常利益", "ordinary_income"),
        ("純利益", "net_income")
    ]

    rows = []

    for item_name, metric in items:

        prior_value = prior.get(metric)
        current_value = current.get(metric)
        next_value = next_.get(metric)

        row = {
            "項目": item_name,
            f"{prior_year}/{fiscal_month}期\n金額":
                format_amount(prior_value),
            f"{prior_year}/{fiscal_month}期\n利益率":
                "-" if metric == "revenue"
                else get_margin(prior_value, prior.get("revenue")),
            f"{current_year}/{fiscal_month}期\n金額":
                format_amount(current_value),
            f"{current_year}/{fiscal_month}期\n利益率":
                "-" if metric == "revenue"
                else get_margin(current_value, current.get("revenue")),
            f"{current_year}/{fiscal_month}期\n成長率":
                get_pct_string(current_value, prior_value),
            f"{next_year}/{fiscal_month}期\n金額":
                format_amount(next_value),
            f"{next_year}/{fiscal_month}期\n利益率":
                "-" if metric == "revenue"
                else get_margin(next_value, next_.get("revenue")),
            f"{next_year}/{fiscal_month}期\n成長率":
                get_pct_string(next_value, current_value)
        }

        rows.append(row)

    growth_df = pd.DataFrame(rows)

    #
    # 色付け
    #
    def style_table(df):
        styles = pd.DataFrame(
            "",
            index=df.index,
            columns=df.columns
        )
        # 2期前（灰色）
        styles.iloc[:, 1:3] = "background-color:#fafafa"
        # 直近期（水色）
        styles.iloc[:, 3:6] = "background-color:#eef7ff"
        # 次期（薄緑）
        styles.iloc[:, 6:9] = "background-color:#e1fff1"
        # 成長率の色
        for col in df.columns:
            if "成長率" in col:
                for idx in df.index:
                    val = str(df.loc[idx, col])
                    if val.startswith("+"):
                        styles.loc[idx, col] += "; color:green; font-weight:bold"
                    elif val.startswith("-") and val != "-":
                        styles.loc[idx, col] += "; color:red; font-weight:bold"
        return styles

    styled_df = (
        growth_df.style
        .apply(style_table, axis=None)
    )

    st.dataframe(
        styled_df,
        hide_index=True,
        use_container_width=True
    )


def render_growth_table(stock_meta):

    st.write("#### 📈 通期実績・通期予想")
    annual = stock_meta.get("annual_performance", {}) or {}
    history = annual.get("history", {})
    if not history:
        st.info("通期データがありません。")
        return
    fiscal_month = stock_meta.get("analyzed_period")
    match = re.search(r"(\d+)月期", str(fiscal_month))
    fiscal_month = int(match.group(1)) if match else ""
    items = [
        ("売上高", "revenue"),
        ("売上総利益", "gross_profit"),
        ("営業利益", "operating_income"),
        ("経常利益", "ordinary_income"),
        ("純利益", "net_income"),
    ]

    # 年度順
    years = sorted(history.keys(), key=int)
    rows = []
    for item_name, metric in items:
        row = {
            "項目": item_name
        }
        prev_value = None
        for year in years:
            data = history[year]
            value = data.get(metric)
            revenue = data.get("revenue")
            data_type = data.get("type", "actual")
            title = f"{year}/{fiscal_month}期"
            if data_type == "forecast":
                title += "(予)"
            row[f"{title}\n金額"] = format_amount(value)
            row[f"{title}\n利益率"] = (
                "-"
                if metric == "revenue"
                else get_margin(value, revenue)
            )
            if prev_value is None:
                row[f"{title}\n成長率"] = "-"
            else:
                row[f"{title}\n成長率"] = get_pct_string(
                    value,
                    prev_value
                )
            prev_value = value
        rows.append(row)
    growth_df = pd.DataFrame(rows)
    #
    # 色付け
    #
    def style_table(df):
        styles = pd.DataFrame(
            "",
            index=df.index,
            columns=df.columns
        )
        col = 1
        for year in years:
            data_type = history[year].get("type")
            if data_type == "forecast":
                color = "#e1fff1"      # 薄緑
            else:
                color = "#eef7ff"      # 水色
            styles.iloc[:, col:col+3] = f"background-color:{color}"
            col += 3
        # 成長率
        for col_name in df.columns:
            if "成長率" not in col_name:
                continue
            for idx in df.index:
                val = str(df.loc[idx, col_name])
                if val.startswith("+"):
                    styles.loc[idx, col_name] += ";color:green;font-weight:bold"
                elif val.startswith("-") and val != "-":
                    styles.loc[idx, col_name] += ";color:red;font-weight:bold"

        return styles
    styled_df = (
        growth_df.style
        .apply(style_table, axis=None)
    )
    st.dataframe(
        growth_df,
        hide_index=True,
        use_container_width=True
    )





def get_progress_judgement(progress_pct, quarter):

    if progress_pct is None:
        return "-"

    # 目安
    target_map = {
        "1Q": 25,
        "2Q": 50,
        "3Q": 75
    }

    target = target_map.get(quarter)

    if target is None:
        return "-"

    ratio = progress_pct / target

    if ratio >= 1.15:
        return "◎ 上振れ期待"
    elif ratio >= 1.0:
        return "○ 順調"
    elif ratio >= 0.85:
        return "△ やや遅れ"
    else:
        return "× 遅れ"


def render_progress_table(stock_meta, combined_data):

    fiscal_month = stock_meta.get("analyzed_period")
    fiscal_month = int(fiscal_month.split("年")[1].split("月期")[0])
    period_str = stock_meta.get("analyzed_period", "")

    # 4Qなら表示しない
    if "4Q" in period_str:
        return

    try:
        fiscal_year = int(period_str[:4])

        if "1Q" in period_str:
            q = "1Q"
        elif "2Q" in period_str:
            q = "2Q"
        elif "3Q" in period_str:
            q = "3Q"
        else:
            return

    except:
        return

    current_key = f"{fiscal_year}_{q}"
    prior_key = f"{fiscal_year-1}_{q}"

    current_data = combined_data.get(current_key, {})
    prior_data = combined_data.get(prior_key, {})

    ap = stock_meta.get("annual_performance", {})
    forecast = ap.get("next_year_forecast", {})

    metrics = [
        ("売上高", "revenue"),
        ("営業利益", "operating_income"),
        ("純利益", "net_income")
    ]

    rows = []

    for name, key in metrics:

        current_value = current_data.get(key)
        prior_value = prior_data.get(key)
        forecast_value = forecast.get(key)

        # 前年同期比
        if current_value and prior_value:
            yoy = (current_value-prior_value)/prior_value*100
            yoy_str = f"{yoy:+.1f}%"
        else:
            yoy_str = "-"

        # 進捗率
        if current_value and forecast_value:
            progress = current_value/forecast_value*100
            progress_str = f"{progress:.1f}%"
        else:
            progress = None
            progress_str = "-"

        rows.append({
            "項目": name,
            f"{fiscal_year-1}年{fiscal_month}月期{q}":
                f"{prior_value:,.0f} 百万円" if prior_value else "-",

            f"{fiscal_year}年{fiscal_month}月期{q}":
                f"{current_value:,.0f} 百万円" if current_value else "-",

            "前年同期比":
                yoy_str,

            "通期予想進捗率":
                progress_str,

            "達成度判定":
                get_progress_judgement(progress, q)
        })

    df = pd.DataFrame(rows)

    def style_table(df):

        styles = pd.DataFrame(
            "",
            index=df.index,
            columns=df.columns
        )

        # 前年同期
        styles.iloc[:,1] = "background-color:#fafafa"

        # 当期
        styles.iloc[:,2] = "background-color:#eef7ff"

        # 前年同期比
        for col in df.columns:
            if "前年同期比" in col:

                for idx in df.index:

                    val = str(df.loc[idx,col])

                    if val.startswith("+"):
                        styles.loc[idx,col] = (
                            "color:green;font-weight:bold"
                        )

                    elif val.startswith("-") and val != "-":
                        styles.loc[idx,col] = (
                            "color:red;font-weight:bold"
                        )

        # 判定列
        for idx in df.index:

            judge = df.loc[idx,"達成度判定"]

            if "◎" in judge:
                styles.loc[idx,"達成度判定"] = (
                    "background-color:#d8f5d8;font-weight:bold"
                )

            elif "○" in judge:
                styles.loc[idx,"達成度判定"] = (
                    "background-color:#edf7d6"
                )

            elif "△" in judge:
                styles.loc[idx,"達成度判定"] = (
                    "background-color:#fff2cc"
                )

            elif "×" in judge:
                styles.loc[idx,"達成度判定"] = (
                    "background-color:#ffd6d6;font-weight:bold"
                )

        return styles

    st.write("#### 📊 四半期進捗状況")

    st.dataframe(
        df.style.apply(style_table, axis=None),
        hide_index=True,
        use_container_width=True
    )

    if stock_meta.get("net_income_forecast"):
        ap = stock_meta.get("annual_performance", {})
        next_ap = ap.get("next_year_forecast", {})
        net_income = next_ap.get("net_income", {})

        if stock_meta.get("net_income_forecast")/1000000  != net_income:
            st.write("★★★業績予想の修正あり★★★")
            st.write(f"純利益  ：  {net_income}百万円    ---→    {stock_meta.get("net_income_forecast")/1000000}百万円")
    

