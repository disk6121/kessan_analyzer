import sqlite3
import pandas as pd
import streamlit as st
import yfinance as yf

from database.supabase_client import supabase

# ---------------------------------------------------------
# 移行テスト完了
# ---------------------------------------------------------

USE_SUPABASE = True


# --- 💾 データベース（SQLite）の初期化と管理関数 ---
DB_NAME = "investment_db.sqlite"

def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # 企業マスター兼ウォッチリスト
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            ticker TEXT PRIMARY KEY,
            company_name TEXT,
            analyzed_period TEXT,
            saved_date TEXT,
            current_price REAL,
            per REAL,
            pbr REAL,
            div_yield REAL,
            is_favorite INTEGER DEFAULT 0,
            investment_memo TEXT DEFAULT '',
            financial_meta_json TEXT,
            annual_perf_json TEXT,
            buy_target REAL,
            sell_target REAL,
            user_forecast_json TEXT
        )
    """)
    # 業績時系列データ（JSONとしてまるごと保存）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS initial_data (
            ticker TEXT PRIMARY KEY,
            combined_data_json TEXT,
            seg_data_json TEXT,
            ai_deep_dive_json TEXT,
            deep_dive_memo TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT
        )
    """)

    conn.commit()
    conn.close()



#1-1 テスト済み
def get_watchlist_supabase():
    response = (
        supabase
        .table("companies")
        .select("*")
        .execute()
    )
    return pd.DataFrame(response.data)


#1-2 テスト済み
def get_watchlist_sqlite():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM companies", conn)
    conn.close()
    return df


#1-3 テスト済み
def get_watchlist():
    if USE_SUPABASE:
        return get_watchlist_supabase()
    else:
        return get_watchlist_sqlite()


#2-1 テスト済み
def delete_company_supabase(ticker):
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

#2-2 テスト済み
def delete_company_sqlite(ticker):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM companies WHERE ticker = ?", (ticker,))
    cursor.execute("DELETE FROM initial_data WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()


#2-3 テスト済み
def delete_company(ticker):
    if USE_SUPABASE:
        delete_company_supabase(ticker)
    else:
        delete_company_sqlite(ticker)



#3-1 テスト済み
def refresh_watchlist_prices_batch_supabase():

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


#3-2 テスト済み
def refresh_watchlist_prices_batch_sqlite():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT ticker
        FROM companies
        """,
        conn
    )
    if df.empty:
        conn.close()
        return
    tickers = [
        f"{x}.T"
        for x in df["ticker"].astype(str)
    ]
    try:
        prices = yf.download(
            tickers=tickers,
            period="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False
        )
        cursor = conn.cursor()
        for ticker in df["ticker"]:
            yf_code = f"{ticker}.T"
            try:
                latest_price = float(
                    prices[yf_code]["Close"].iloc[-1]
                )
                cursor.execute(
                    """
                    UPDATE companies
                    SET current_price = ?
                    WHERE ticker = ?
                    """,
                    (
                        latest_price,
                        ticker
                    )
                )
            except:
                pass
        conn.commit()
    except Exception as e:
        st.error(
            f"株価取得エラー: {e}"
        )
    finally:
        conn.close()

#3-3 テスト済み
def refresh_watchlist_prices_batch():
    if USE_SUPABASE:
        refresh_watchlist_prices_batch_supabase()
    else:
        refresh_watchlist_prices_batch_sqlite()
