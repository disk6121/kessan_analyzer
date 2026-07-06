
import streamlit as st
import pandas as pd

def render_segment_editor(ticker,seg_by_quarter):

    if seg_by_quarter and isinstance(seg_by_quarter, dict):
        
        with st.expander("⚙️ セグメント別 四半期累計業績"):
        
            # 1. すべての四半期キーとセグメントデータをフラットなリストに変換
            flat_seg_records = []
            q_order = {"1Q": 1, "2Q": 2, "3Q": 3, "4Q": 4}
            sorted_q_keys = sorted(
                [k for k in seg_by_quarter.keys() if "_" in k],
                key=lambda x: (int(x.split("_")[0]) if x.split("_")[0].isdigit() else 0, q_order.get(x.split("_")[1], 0))
            )
           
            # データの内部書き戻し用に、要素のインデックスを保持
            for q_key in sorted_q_keys:
                year_str, q_str = q_key.split("_")
                seg_list = seg_by_quarter[q_key]

                if isinstance(seg_list, list):
                    for idx, s in enumerate(seg_list):
                        flat_seg_records.append({
                            "Key": q_key,
                            "Idx": idx,
                            "決算期": f"{year_str}年度 {q_str} (累計)",
                            "セグメント名": s.get("name", ""),
                            "売上高 (百万円)": float(s.get("revenue_million") or 0),
                            "営業利益 (百万円)": float(s.get("profit_million") or 0)
                        })
           
            if flat_seg_records:
                df_seg_input = pd.DataFrame(flat_seg_records)

                # 2. 1つのデータエディタでセグメント名も含めて一括編集できるようにする
                edited_seg_df = st.data_editor(
                    df_seg_input,
                    column_config={
                        "Key": None,  # 内部識別キーを隠す
                        "Idx": None   # 配列インデックスを隠す
                    },
                    use_container_width=True,
                    hide_index=True,
                    key=f"seg_global_editor_{ticker}"
                )
               
                # 3. 💡 【リアルタイム上書き】編集結果を元のデータ構造へ正しく書き戻す
                if edited_seg_df is not None:
                    for _, row in edited_seg_df.iterrows():
                        k = row["Key"]
                        i = int(row["Idx"])
                        
                        # 元のリストの該当インデックスにある辞書を直接書き換える
                        if k in seg_by_quarter and i < len(seg_by_quarter[k]):
                            seg_by_quarter[k][i]["name"] = row["セグメント名"]
                            seg_by_quarter[k][i]["revenue_million"] = float(row["売上高 (百万円)"])
                            seg_by_quarter[k][i]["profit_million"] = float(row["営業利益 (百万円)"])
            else:
                st.info("抽出された報告セグメントがありません。")