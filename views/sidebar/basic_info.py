
import streamlit as st
import pandas as pd

def render_basic_info(stock_meta):

    with st.expander("⚙️ 基礎情報"):

        meta_df = pd.DataFrame.from_dict({
            "項目": ["証券コード", "企業名", "上場区分"],
            "値": [
                stock_meta.get("ticker"),
                stock_meta.get("company_name"),
                stock_meta.get("exchange_name")
            ]
        })
        edited_meta = st.data_editor(meta_df, hide_index=True, use_container_width=True, num_rows="fixed",disabled=["項目"], key="meta_editor")

        if edited_meta is not None:
            new_vals = edited_meta["値"].tolist()
            stock_meta["ticker"] = new_vals[0]
            stock_meta["company_name"] = new_vals[1]
            stock_meta["exchange_name"] = new_vals[2]
