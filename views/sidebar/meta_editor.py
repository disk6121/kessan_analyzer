
import streamlit as st
import pandas as pd


def render_meta_editor(stock_meta):

    with st.expander("⚙️ 株価・各種財務指数"):
                
        ap = stock_meta.get("annual_performance", {}) or {}
        ticker = stock_meta.get("ticker")
        shares_issued = stock_meta.get("shares_issued", 0) or 0
        treasury_shares = stock_meta.get("treasury_shares", 0) or 0
       
        edit_meta_df = pd.DataFrame({
            "項目": [
                "最新株価 (円)",
                "今期純利益予想 (円)",
                "純資産 (円)",
                "非支配株主持分 (円)",
                "予想配当金 (円)",
                "発行済株式数 (株)",
                "自己株式数 (株)",
                "EPS（円）",
                "希薄化後EPS(円)"
            ],
            "値": [
                float(stock_meta.get("current_price") or 0),
                float(stock_meta.get("net_income_forecast") or 0),
                float(stock_meta.get("net_assets") or 0),
                float(stock_meta.get("non_controlling_interests") or 0), 
                float(stock_meta.get("dividend_forecast") or 0),
                float(shares_issued),
                float(treasury_shares),
                float(stock_meta.get("eps_basic") or 0),
                float(stock_meta.get("eps_diluted")  or 0)
            ]
        })

        edited_meta = st.data_editor(edit_meta_df, width="stretch", hide_index=True, key=f"meta_editor_{ticker}")

        # 💡 編集された値を stock_meta および ap にリアルタイム上書き
        if edited_meta is not None:
            new_vals = edited_meta["値"].tolist()
            stock_meta["current_price"] = new_vals[0]
            stock_meta["net_income_forecast"] = new_vals[1]
            stock_meta["net_assets"] = new_vals[2]
            stock_meta["non_controlling_interests"] = new_vals[3]
            stock_meta["dividend_forecast"] = new_vals[4]
            stock_meta["shares_issued"] = new_vals[5]
            stock_meta["treasury_shares"] = new_vals[6]
            stock_meta["eps_basic"] = new_vals[7]
            stock_meta["eps_diluted"] = new_vals[8]
           
            # 💡 【自動再計算】上書きされた新しい値を使って、PER/PBR/利回り/時価総額を即座に再計算
            ns = stock_meta["shares_issued"] - stock_meta["treasury_shares"]
            if ns > 0 and stock_meta["current_price"] > 0:
                # 予想PER
                if stock_meta["net_income_forecast"] > 0:
                    stock_meta["per"] = stock_meta["current_price"] / (stock_meta["net_income_forecast"] / ns)
                # PBR
                if stock_meta["net_assets"] > 0:
                    stock_meta["pbr"] = stock_meta["current_price"] / (stock_meta["net_assets"] / ns)
                # 配当利回り
                    if stock_meta["dividend_forecast"] > 0:
                        stock_meta["div_yield"] = (stock_meta["dividend_forecast"] / stock_meta["current_price"]) * 100

