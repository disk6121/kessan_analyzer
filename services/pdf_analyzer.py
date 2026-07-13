import json
import os
import streamlit as st
from google import genai
from google.genai import types

from services.gemini_service import generate_content_with_retry
from services.stock_price_service import enrich_stock_price
from services.market_service import get_exchange_name
from database.load_repository import load_company


# ---------------------------------------------------------
# PDF読み込み、市場区分、株価取得　→　"meta"、"combined"、"seg"　を作成
# ---------------------------------------------------------

def analyze_pdfs(
        uploaded_files,
        api_key
):

        combined_data = {}
        seg_by_quarter = {}
        stock_meta = {"ticker": None, "company_name": None, "analyzed_period": "不明", "annual_performance": {}}

        client = genai.Client(api_key=api_key)
        prompt = """
        添付された決算資料から、以下の情報を厳密に抽出してください。
        1. 資料の会計決算期および四半期判定（例: 2026年3月期 3Q）
        2. 決算期の「対象年度（西暦4桁）」および「四半期（1Q, 2Q, 3Q, 4Q）」
        3. 証券コード（4桁の数字）および企業名
        4. 投資指標・財務用データ(基本的1株当たり純利益、潜在株式調整後（希薄化後）1株当たり純利益を含む。)
        5. セグメント別情報
        6. 通期業績データ
       
        必ず以下のJSON構造のみで出力してください。有効なJSONのみを出力してください。JSONは、json.loadでそのまま読み込める形式にしてください。
        {
          "detected_fiscal_year": 2026,
          "detected_quarter": "3Q",
          "ticker": "7203",
          "company_name": "トヨタ自動車",
          "analyzed_period": "2026年3月期 3Q",
          "this_period_data": {"revenue": 3200, "operating_income": 320},
          "prior_period_data": {"revenue": 2900, "operating_income": 290},
          "investment_meta": {
            "net_income_forecast_million": 4500000, "net_assets_million": 35000000, "non_controlling_interests_million": 900000, "dividend_forecast_yen": 75,
            "shares_issued_count": 16314987460, "treasury_shares_count": 314987460, "cash_and_deposits_million": 5000000,
            "interest_bearing_debt_million": 12000000, "equity_ratio_percent": 38.5, "eps_basic_yen": 123.45, "eps_diluted_yen": 120.87
          },
          "this_period_segments": [{"name": "自動車", "revenue_million": 3000, "profit_million": 280}],
          "prior_period_segments": [{"name": "自動車", "revenue_million": 2700, "profit_million": 250}],
          "annual_performance": {
            "prior_year_actual": {"fiscal_year": 2025, "revenue": 38000000, "gross_profit": 14500000, "operating_income": 4000000, "ordinary_income": 4200000, "net_income": 3500000, "_source_quarter": "4Q"},
            "current_year_actual_or_forecast": {"fiscal_year": 2026, "revenue": 43000000, "gross_profit": 16800000, "operating_income": 4900000, "ordinary_income": 5000000, "net_income": 4500000},
            "next_year_forecast": {"fiscal_year": 2027, "revenue": 45000000, "gross_profit": 17600000, "operating_income": 5100000, "ordinary_income": 5300000, "net_income": 4700000}
          }
        }
        """
        progress_bar = st.progress(0)
      
        latest_period_candidate = (0, 0, "不明")
        q_mapping = {"1Q": 1, "2Q": 2, "3Q": 3, "4Q": 4}

        for index, file in enumerate(uploaded_files):
            st.write(f"📄 {file.name} を解析中...")
            try:
                temp_path = f"temp__upload_{index}.pdf"
                with open(temp_path, "wb") as f: f.write(file.getbuffer())
                pdf_file = client.files.upload(file=temp_path)
     
                response = generate_content_with_retry(
                    client=client,
                    model='gemini-2.5-flash',
                    contents=[pdf_file, prompt],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
     
                client.files.delete(name=pdf_file.name)
                if os.path.exists(temp_path): os.remove(temp_path)

                try:
                    res_json = json.loads(response.text)
                except json.JSONDecodeError as e:
                    st.error(f"Geminiが不正なJSONを返しました: {e}")
                    error_file = f"json_error_{file.name}.txt"
                    with open(error_file, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    st.info(f"Geminiの返答を {error_file} に保存しました。")
                    continue

                f_year = res_json.get("detected_fiscal_year")
                q = res_json.get("detected_quarter")

                if f_year and q in ["1Q", "2Q", "3Q", "4Q"]:
                    this_key = f"{f_year}_{q}"
                    prev_key = f"{f_year-1}_{q}"

                    combined_data[this_key] = res_json.get("this_period_data")
                    if res_json.get("this_period_segments"):
                        seg_by_quarter[this_key] = res_json.get("this_period_segments")

                    combined_data[prev_key] = res_json.get("prior_period_data")
                    if res_json.get("prior_period_segments"):
                        seg_by_quarter[prev_key] = res_json.get("prior_period_segments")
             
                if res_json.get("ticker"):
                    stock_meta["ticker"] = res_json.get("ticker")
                    stock_meta["company_name"] = res_json.get("company_name")
                     
                    p_str = res_json.get("analyzed_period", "不明")
                    current_score = (int(f_year) if f_year else 0, q_mapping.get(q, 0))
                    if current_score >= (latest_period_candidate[0], latest_period_candidate[1]):
                        latest_period_candidate = (current_score[0], current_score[1], p_str)

                    meta = res_json.get("investment_meta", {})
                    for k, v in [("net_income_forecast", "net_income_forecast_million"), ("net_assets", "net_assets_million"), ("non_controlling_interests", "non_controlling_interests_million")]:
                        if meta.get(v) is not None: stock_meta[k] = meta[v] * 1000000
                    if meta.get("dividend_forecast_yen") is not None: stock_meta["dividend_forecast"] = meta["dividend_forecast_yen"]
                    if meta.get("shares_issued_count") is not None: stock_meta["shares_issued"] = meta["shares_issued_count"]
                    if meta.get("treasury_shares_count") is not None: stock_meta["treasury_shares"] = meta["treasury_shares_count"]
                    if meta.get("cash_and_deposits_million") is not None: stock_meta["cash_and_deposits"] = meta["cash_and_deposits_million"]
                    if meta.get("interest_bearing_debt_million") is not None: stock_meta["interest_bearing_debt"] = meta["interest_bearing_debt_million"]
                    if meta.get("equity_ratio_percent") is not None: stock_meta["equity_ratio"] = meta["equity_ratio_percent"]
                    if meta.get("eps_basic_yen") is not None: stock_meta["eps_basic"] = float(meta["eps_basic_yen"])
                    if meta.get("eps_diluted_yen") is not None: stock_meta["eps_diluted"] = float(meta["eps_diluted_yen"])
                       
                    if res_json.get("annual_performance"):
                            if q == "4Q":
                                    stock_meta["annual_performance"] = res_json["annual_performance"]

            except Exception as e:
                st.error(f"❌ {file.name} の処理中にエラー: {e}")
          
            import time
            time.sleep(2)
            progress_bar.progress((index + 1) / len(uploaded_files))

        stock_meta["analyzed_period"] = latest_period_candidate[2]

        ticker = stock_meta.get("ticker")
        if ticker:
            try:
                stock_meta["exchange_name"] = get_exchange_name(ticker)
                stock_meta = enrich_stock_price(stock_meta)

            except:
                pass

        st.session_state.current_analysis = {"meta": stock_meta, "combined": combined_data, "seg": seg_by_quarter, "ai_report": None}

        return {
            "meta": stock_meta,
            "combined": combined_data,
            "seg": seg_by_quarter
        }

