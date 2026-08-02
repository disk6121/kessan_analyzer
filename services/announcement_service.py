
from datetime import date
import pandas as pd
import streamlit as st


@st.cache_data
def load_schedule(excel_path) -> pd.DataFrame:
    """
    JPXの決算発表予定Excelを読み込み、
    必要な列だけを返す。

    Returns
    -------
    DataFrame
        columns:
            ticker
            company_name
            announcement_date
            announcement_type
    """

    df = pd.read_excel(
        excel_path,
        sheet_name="List",
        header=4
    )

    df = df.rename(columns={
        "コード\nCode": "ticker",
        "会社名": "company_name",
        "決算発表予定日\nScheduled Dates for Earnings Announcements": "announcement_date",
        "種別": "announcement_type"
    })

    df = df[[
        "ticker",
        "company_name",
        "announcement_date",
        "announcement_type"
    ]]

    # 証券コードは4桁文字列に統一
    df["ticker"] = (
        df["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # 日付型へ変換
    df["announcement_date"] = pd.to_datetime(
        df["announcement_date"],
        errors="coerce"
    )

    return df


@st.cache_data 
def get_schedule_dict(excel_path) -> dict:
    """
    tickerをキーにした辞書を返す。

    Returns
    -------
    {
        "7203": {
            "company_name": "...",
            "announcement_date": Timestamp(...),
            "announcement_type": "第1四半期"
        },
        ...
    }
    """

    df = load_schedule(excel_path)

    schedule = {}

    for _, row in df.iterrows():

        schedule[row["ticker"]] = {
            "company_name": row["company_name"],
            "announcement_date": row["announcement_date"],
            "announcement_type": row["announcement_type"]
        }

    return schedule


def get_company_schedule(ticker, schedule_dict):
    """
    指定銘柄の決算予定情報を取得

    Returns
    -------
    dict または None
    """

    return schedule_dict.get(str(ticker))



def get_days_until_announcement(announcement_date):
    """
    決算までの日数を返す。

    Returns
    -------
    "今日"
    "明日"
    "あと5日"
    ""
    """

    if pd.isna(announcement_date):
        return ""

    target = announcement_date.date()

    diff = (target - date.today()).days

    if diff < 0:
        return "発表済"

    if diff == 0:
        return "今日"

    if diff == 1:
        return "明日"

    return f"あと{diff}日"


def get_days_diff(announcement_date):
    """
    今日との差（日数）

    今日      = 0
    明日      = 1
    昨日      = -1
    5日前     = -5
    """

    if pd.isna(announcement_date):
        return None

    return (announcement_date.date() - date.today()).days


