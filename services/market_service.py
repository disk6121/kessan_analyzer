import pandas as pd
import os
import streamlit as st

# ---------------------------------------------------------
# 市場区分の判定
# ---------------------------------------------------------


def get_exchange_name(ticker,excel_file="data_j.xlsx"):

    # ファイルが存在するか確認
    if os.path.exists(excel_file):
        try:
            # 東証のExcelを読み込み
            jpx_df = pd.read_excel(excel_file, dtype={"コード": str})

            ticker = str(ticker).strip()
                           
            # Excelの「コード」列と入力された4桁コードを数値として比較して一致する行を探す
            matched = jpx_df[jpx_df["コード"].str.strip() == ticker]
                            
            if not matched.empty:
                # 東証Excelの「市場・商品区分」列を取得（例: 「プライム（内国株式）」など）
                raw_market = str(matched["市場・商品区分"].iloc[0])
                                
                # 文字列を「東証プライム」などの綺麗な形に整形
                if "プライム" in raw_market:
                    return "東証プライム"
                elif "スタンダード" in raw_market:
                    return "東証スタンダード"
                elif "グロース" in raw_market:
                    return "東証グロース"
                else:
                    return "その他" # その他の区分（プロマーケット等）
            else:
                return "その他" # 該当コードがない場合
        except Exception as e:
            st.warning(f"Excelデータの解析中にエラーが発生しました: {e}")
            return "不明"
    else:
        # Excelファイルが同フォルダに見つからない場合の警告
        st.warning(f"⚠️ '{excel_file}' が見つからないため、市場区分を特定できませんでした。")
        return "不明"
