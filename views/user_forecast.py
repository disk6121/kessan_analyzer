
import streamlit as st
import pandas as pd
import re
import json
import math

from services.forecast_service import update_user_forecast


def to_number(value):
    """数値変換。欠損・不正値はNone。"""
    try:
        if value is None:
            return None

        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except (TypeError, ValueError):
        return None


def parse_json_dict(value):
    """JSON文字列またはdictをdictに変換。"""
    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            result = json.loads(value)
            return result if isinstance(result, dict) else {}
        except (ValueError, TypeError):
            return {}

    return {}


def calculate_ttm(combined_data, period_str):
    """
    直近1年実績を計算する。
    TTM = 当期累計 - 前年同期累計 + 前期通期実績
    """

    result = {
        "revenue": None,
        "operating_income": None,
        "net_income": None
    }

    if not isinstance(combined_data, dict):
        return result

    match = re.search(
        r"(\d+)年.*?(\d+)Q",
        str(period_str)
    )

    if not match:
        return result

    fiscal_year = int(match.group(1))
    quarter = int(match.group(2))

    # 4QはTTM計算対象外
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

        try:
            values = [to_number(v) for v in values]

            if any(v is None for v in values):
                continue

            result[metric] = (
                values[0]
                - values[1]
                + values[2]
            )

        except (TypeError, ValueError):
            continue

    return result


def get_latest_forecast(annual_perf):
    """
    ANNUAL_PERF_JSONから最新の今期予想を取得する。
    """

    history = annual_perf.get("history", {})

    if not isinstance(history, dict):
        return {}

    forecasts = []

    for key, data in history.items():

        if not isinstance(data, dict):
            continue

        if data.get("type") != "forecast":
            continue

        year = data.get("fiscal_year")

        if year is None:
            try:
                year = int(key)
            except (TypeError, ValueError):
                year = 0

        forecasts.append((int(year), data))

    if not forecasts:
        return {}

    forecasts.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return forecasts[0][1]


def calculate_dilution_ratio(financial_meta):
    """
    希薄化率 = 希薄化後EPS / 基本EPS

    データがない場合は1.0とする。
    """

    eps_basic = to_number(
        financial_meta.get("eps_basic")
    )

    eps_diluted = to_number(
        financial_meta.get("eps_diluted")
    )

    if (
        eps_basic is None
        or eps_diluted is None
        or eps_basic == 0
        or eps_diluted == 0
    ):
        return 1.0

    return eps_diluted / eps_basic


def calculate_parent_ratio(financial_meta):
    """
    支配株主持分率 =
    (純資産 - 非支配株主持分) / 純資産

    データがない場合は1.0とする。
    """

    net_assets = to_number(
        financial_meta.get("net_assets")
    )

    non_controlling = to_number(
        financial_meta.get("non_controlling_interests")
    )

    if net_assets is None or net_assets <= 0:
        return 1.0

    if non_controlling is None:
        non_controlling = 0

    return (
        net_assets - non_controlling
    ) / net_assets


def calculate_auto_forecast(
    stock_meta,
    combined_data,
    ttm
):
    """
    独自予想1期目の自動計算。
    """

    annual_perf = parse_json_dict(
        combined_data.get("annual_perf_json")
    )

    financial_meta = parse_json_dict(
        stock_meta.get("financial_meta_json")
    )

    forecast = get_latest_forecast(annual_perf)

    if not forecast:
        return None, "今期予想データが見つかりません。"

    period_str = str(
        stock_meta.get("analyzed_period", "")
    )

    match = re.search(
        r"(\d+)年.*?(\d+)Q",
        period_str
    )

    if not match:
        return None, "決算期を判定できません。"

    quarter = int(match.group(2))

    # 希薄化率・支配株主持分率
    dilution_ratio = calculate_dilution_ratio(
        financial_meta
    )

    parent_ratio = calculate_parent_ratio(
        financial_meta
    )

    # 今期予想
    forecast_revenue = to_number(
        forecast.get("revenue")
    )

    forecast_operating = to_number(
        forecast.get("operating_income")
    )

    forecast_ordinary = to_number(
        forecast.get("ordinary_income")
    )

    # 4Qの場合
    if quarter == 4:

        revenue = forecast_revenue

        operating_income = forecast_operating

        # 経常利益が空欄なら営業利益を採用
        ordinary_income = (
            forecast_ordinary
            if forecast_ordinary is not None
            else forecast_operating
        )

    # 1Q～3Qの場合
    else:

        revenue = to_number(
            ttm.get("revenue")
        )

        operating_income = to_number(
            ttm.get("operating_income")
        )

        if operating_income is None:
            return None, "直近1年実績の営業利益を計算できません。"

        # 今期予想の営業利益・経常利益の差額を反映
        if (
            forecast_operating is not None
            and forecast_ordinary is not None
        ):

            ordinary_income = (
                operating_income
                - (
                    forecast_operating
                    - forecast_ordinary
                )
            )

        else:
            # 今期予想利益が空欄の場合
            ordinary_income = operating_income

    if ordinary_income is None:
        return None, "経常利益を計算できません。"

    # 純利益
    net_income = (
        ordinary_income
        * 0.7
        * dilution_ratio
        * parent_ratio
    )

    result = {
        "revenue": revenue,
        "gross_profit": None,
        "operating_income": operating_income,
        "ordinary_income": ordinary_income,
        "net_income": net_income
    }

    return result, None


def render_user_forecast(stock_meta, combined_data=None):

    ticker = stock_meta["ticker"]

    user_fc = stock_meta.get("user_forecast", {})

    st.write("#### ✏️ 独自予想")

    if not isinstance(user_fc, dict):
        user_fc = {}

    year1 = user_fc.get("year1", {})
    year2 = user_fc.get("year2", {})

    if not isinstance(year1, dict):
        year1 = {}

    if not isinstance(year2, dict):
        year2 = {}

    period_str = stock_meta.get("analyzed_period", "")

    combined_data = combined_data or {}

    # 直近1年実績
    ttm = calculate_ttm(
        combined_data,
        period_str
    )

    period_match = re.search(
        r"(\d+)年.*?(\d+)Q",
        str(period_str)
    )

    is_ttm_display = (
        period_match is not None
        and int(period_match.group(2)) != 4
    )

    def format_ttm(value):
        if value is None:
            return "-"
        return f"{value:,.0f}"

    rows = [
        {
            "項目": "売上高",
            **(
                {"直近1年実績": format_ttm(ttm["revenue"])}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("revenue"),
            "独自予想(2期目)": year2.get("revenue")
        },
        {
            "項目": "売上総利益",
            **(
                {"直近1年実績": "-"}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("gross_profit"),
            "独自予想(2期目)": year2.get("gross_profit")
        },
        {
            "項目": "営業利益",
            **(
                {"直近1年実績": format_ttm(ttm["operating_income"])}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("operating_income"),
            "独自予想(2期目)": year2.get("operating_income")
        },
        {
            "項目": "経常利益",
            **(
                {"直近1年実績": "-"}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("ordinary_income"),
            "独自予想(2期目)": year2.get("ordinary_income")
        },
        {
            "項目": "純利益",
            **(
                {"直近1年実績": format_ttm(ttm["net_income"])}
                if is_ttm_display else {}
            ),
            "独自予想(1期目)": year1.get("net_income"),
            "独自予想(2期目)": year2.get("net_income")
        }
    ]

    forecast_df = pd.DataFrame(rows)

    # --------------------------------
    # 1期目自動計算ボタン
    # --------------------------------

    editor_key = f"user_forecast_editor_{ticker}"

    if st.button(
        "🧮 1期目を自動計算",
        key=f"auto_forecast_{ticker}",
        width="stretch"
    ):

        auto_result, error = calculate_auto_forecast(
            stock_meta,
            combined_data,
            ttm
        )

        if error:
            st.error(error)

        else:

            # 既存値をすべて上書き
            forecast_df.loc[
                forecast_df["項目"] == "売上高",
                "独自予想(1期目)"
            ] = auto_result["revenue"]

            forecast_df.loc[
                forecast_df["項目"] == "売上総利益",
                "独自予想(1期目)"
            ] = None

            forecast_df.loc[
                forecast_df["項目"] == "営業利益",
                "独自予想(1期目)"
            ] = auto_result["operating_income"]

            forecast_df.loc[
                forecast_df["項目"] == "経常利益",
                "独自予想(1期目)"
            ] = auto_result["ordinary_income"]

            forecast_df.loc[
                forecast_df["項目"] == "純利益",
                "独自予想(1期目)"
            ] = auto_result["net_income"]

            # data_editorに自動計算結果を反映
            st.session_state[editor_key] = forecast_df.copy()

            st.success("1期目の自動計算が完了しました。")

    # --------------------------------
    # 独自予想入力・保存
    # --------------------------------

    with st.form(key=f"user_forecast_form_{ticker}"):

        col1, col2 = st.columns([4, 6])

        with col1:

            st.write("✏️ 独自収支予想")

            disabled_columns = (
                ["直近1年実績"]
                if is_ttm_display else []
            )

            edited_df = st.data_editor(
                forecast_df,
                hide_index=True,
                width="stretch",
                disabled=disabled_columns,
                key=editor_key
            )

        with col2:

            memo = st.text_area(
                "✏️ 独自予想の根拠",
                value=user_fc.get("memo", ""),
                height=260,
                key=f"user_forecast_memo_{ticker}"
            )

        submitted = st.form_submit_button(
            "💾 独自予想を更新",
            width="stretch"
        )

    if submitted:

        save_df = edited_df.drop(
            columns=["直近1年実績"],
            errors="ignore"
        )

        update_user_forecast(
            stock_meta,
            save_df,
            memo
        )

        st.success("独自予想を更新しました")

