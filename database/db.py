import sqlite3
import pandas as pd
import streamlit as st
import yfinance as yf

from database.supabase_client import supabase

def get_watchlist():
    response = (
        supabase
        .table("companies")
        .select("*")
        .execute()
    )
    return pd.DataFrame(response.data)



def delete_company(ticker):
    # companiesテーブルから削除
    (
        supabase
        .table("companies")
        .delete()
        .eq("ticker", ticker)
        .execute()
    )

    # initial_dataテーブルから削除
    (
        supabase
        .table("initial_data")
        .delete()
        .eq("ticker", ticker)
        .execute()
    )


def refresh_watchlist_prices_batch():

    # ウォッチリスト取得
    response = (
        supabase
        .table("companies")
        .select("ticker")
        .execute()
    )

    df = pd.DataFrame(response.data)
    if df.empty:
        return
    tickers = [f"{t}.T" for t in df["ticker"].astype(str)]
    try:
        prices = yf.download(
            tickers=tickers,
            period="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False
        )
        updates = []
        for ticker in df["ticker"]:
            yf_code = f"{ticker}.T"
            try:
                latest_price = float(
                    prices[yf_code]["Close"].iloc[-1]
                )

                # nanは保存しない
                if pd.notna(latest_price):
                    updates.append({
                        "ticker": str(ticker),
                        "current_price": latest_price
                    })

            except Exception:
                # 株価取得失敗時はスキップ
                continue

        # 一括更新
        if updates:
            (
                supabase
                .table("companies")
                .upsert(
                    updates,
                    on_conflict="ticker"
                )
                .execute()
            )

    except Exception as e:
        st.error(f"株価取得エラー: {e}")



