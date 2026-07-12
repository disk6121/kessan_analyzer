
import streamlit as st
import pandas as pd


def render_quarter_editor(ticker,combined_data):

        with st.expander("⚙️ 四半期業績（累計値）"):
       
            # 現在の累計データを一時的にDataFrame化してエディタに渡す
            cumulative_records = []
            q_order = {"1Q": 1, "2Q": 2, "3Q": 3, "4Q": 4}
            sorted_keys = sorted(combined_data.keys(), key=lambda x: (int(x.split("_")[0]), q_order.get(x.split("_")[1], 0)))
       
            for key in sorted_keys:
                year_str, q_str = key.split("_")
                q_data = combined_data[key]
                if q_data and q_data.get("revenue") is not None:
                    cumulative_records.append({
                        "Key": key, # 内部識別用
                        "決算期": f"{year_str}年度 {q_str}",
                        "売上高 (百万円)": float(q_data.get("revenue")),
                        "営業利益 (百万円)": float(q_data.get("operating_income"))
                    })
       
            if cumulative_records:
                df_cumulative_input = pd.DataFrame(cumulative_records)
                # data_editor で編集可能にする（Key列は非表示）
                edited_perf_df = st.data_editor(
                    df_cumulative_input,
                    column_config={"Key": None}, # Key列を隠す
                    width="stretch",
                    hide_index=True,
                    key=f"perf_editor_{ticker}" # 企業ごとに一意のキーにする
                )
           
                # 💡 ユーザーが編集した内容を元の combined_data にリアルタイム上書き
                for _, row in edited_perf_df.iterrows():
                    k = row["Key"]
                    combined_data[k]["revenue"] = row["売上高 (百万円)"]
                    combined_data[k]["operating_income"] = row["営業利益 (百万円)"]
            else:
                st.info("編集できる累計データがありません。")
