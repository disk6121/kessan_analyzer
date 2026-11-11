import streamlit as st
import pandas as pd
import re

from services.forecast_service import update_user_forecast


def calculate_ttm(combined_data, period_str):
    """
    直近4四半期実績を計算する。
    TTM = 当期累計 - 前年同期累計 + 前期通期実績
    """

    result = {
        "revenue": None,
        "operating_income": None,
        "net_income": None
    }

    if not isinstance(combined_data, dict):
        return result

    # 決算期・四半期を取得
    match = re.search(
        r"(\d+)年.*?(\d+)Q",
        str(period_str)
    )

    if not match:
        return result

    fiscal_year = int(match.group(1))
    quarter = int(match.group(2))

    # 4Qは計算・表示しない
    if quarter == 4:
        return result

    q = f"{quarter}Q"

    current_key = f"{fiscal_year}_{q}"
    prior_key = f"{fiscal_year - 1}_{q}"
    previous_full_year_key = f"{fiscal_year - 1}_4Q"

    current_data = combined_data.get(current_key, {})
    prior_data = combined_data.get(prior_key, {})
    previous_full_year_data = combined_data.get(
        previous_full_year_key, {}
    )

    if not all([
        isinstance(current_data, dict),
        isinstance(prior_data, dict),
        isinstance(previous_full_year_data, dict)
    ]):
        return result

    metrics = [
        "revenue",
        "operating_income",
        "net_income"
    ]

    for metric in metrics:

        values = [
            current_data.get(metric),
            prior_data.get(metric),
            previous_full_year_data.get(metric)
        ]

        # 3つすべてのデータがある場合のみ計算
        try:
            if any(
                value is None or pd.isna(value)
                for value in values
            ):
                continue

            current_value = float(values[0])
            prior_value = float(values[1])
            previous_full_year_value = float(values[2])

            result[metric] = (
                current_value
                - prior_value
                + previous_full_year_value
            )

        except (TypeError, ValueError):
            continue

    return result


def render_user_forecast(stock_meta, combined_data=None):

    ticker = stock_meta["ticker"]
    user_fc = stock_meta.get("user_forecast", {})

    st.write("#### ✏️ 独自予想")

    if not isinstance(user_fc, dict):
        user_fc = {}

    year1 = user_fc.get("year1", {})
    year2 = user_fc.get("year2", {})

    # 直近4四半期実績を計算
    period_str = stock_meta.get("analyzed_period", "")

    ttm = calculate_ttm(
        combined_data or {},
        period_str
    )

    # 4Q以外の場合のみ列を追加
    is_ttm_display = (
        calculate_ttm(combined_data or {}, period_str)
        is not None
        and bool(re.search(r"\d+Q", str(period_str)))
        and not bool(re.search(r"4Q", str(period_str)))
    )

    def format_ttm(value):
        if value is None:
            return "-"
        return f"{value:,.0f} 百万円"

    rows = [
        {
            "項目": "売上高",
            **(
                {"直近4四半期実績": format_ttm(ttm["revenue"])}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("revenue"),
            "独自予想(2期目)": year2.get("revenue")
        },
        {
            "項目": "売上総利益",
            **(
                {"直近4四半期実績": "-"}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("gross_profit"),
            "独自予想(2期目)": year2.get("gross_profit")
        },
        {
            "項目": "営業利益",
            **(
                {"直近4四半期実績": format_ttm(ttm["operating_income"])}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("operating_income"),
            "独自予想(2期目)": year2.get("operating_income")
        },
        {
            "項目": "経常利益",
            **(
                {"直近4四半期実績": "-"}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("ordinary_income"),
            "独自予想(2期目)": year2.get("ordinary_income")
        },
        {
            "項目": "純利益",
            **(
                {"直近4四半期実績": format_ttm(ttm["net_income"])}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("net_income"),
            "独自予想(2期目)": year2.get("net_income")
        }
    ]

    forecast_df = pd.DataFrame(rows)

    with st.form(key=f"user_forecast_form_{ticker}"):

        col1, col2 = st.columns([4, 6])

        with col1:
            st.write("✏️ 独自収支予想")

            disabled_columns = (
                ["直近4四半期実績"]
                if is_ttm_display else []
            )

            edited_df = st.data_editor(
                forecast_df,
                hide_index=True,
                width="stretch",
                disabled=disabled_columns,
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

        # 直近4四半期実績列は保存対象から除外
        save_df = edited_df.drop(
            columns=["直近4四半期実績"],
            errors="ignore"
        )

        update_user_forecast(
            stock_meta,
            save_df,
            memo
        )

        st.success("独自予想を更新しました")
