import yfinance as yf
import streamlit as st

# ---------------------------------------------------------
# 📈 yfinance による最新株価の取得
# ---------------------------------------------------------

def enrich_stock_price(stock_meta):
    ticker = stock_meta.get("ticker")
    if not ticker:
        return stock_meta
    
    stock = yf.Ticker(f"{ticker}.T")
    todays_data = stock.history(period='1d')
    if not todays_data.empty:
        stock_meta["current_price"] = todays_data['Close'].iloc[-1]
        ns = (stock_meta.get("shares_issued", 0) or 0) - (stock_meta.get("treasury_shares", 0) or 0)
                      
        # 予想PERの計算
        def calc_forward_per(price,forecast_profit,shares):
            if not forecast_profit or shares <=0:
                return None
            eps = forecast_profit / shares
            return price / eps

        stock_meta["per"] = calc_forward_per(stock_meta["current_price"],stock_meta.get("net_income_forecast"),ns)

        # PBRの計算
        def calc_pbr(price,net_assets,shares):
            if not net_assets or shares <= 0:
                return None
            bps = net_assets / shares
            return price / bps

        stock_meta["pbr"] = calc_pbr(stock_meta["current_price"],stock_meta.get("net_assets"),ns)

        # 配当利回りの計算
        def calc_div_yield(price,dividend):
            if not dividend:
                return None
            return dividend / price * 100

        stock_meta["div_yield"] = calc_div_yield(stock_meta["current_price"],stock_meta.get("dividend_forecast"))

    return stock_meta



def get_latest_stock_price(ticker):

    try:
        yf_code = f"{str(ticker).strip()}.T"

        prices = yf.download(
            tickers=yf_code,
            period="1d",
            auto_adjust=False,
            progress=False
        )

        if prices is None or prices.empty:
            return None

        close = prices["Close"].dropna()

        if close.empty:
            return None

        return float(close.iloc[-1])

    except Exception as e:
        st.warning(f"株価取得エラー: {e}")
        return None
        
