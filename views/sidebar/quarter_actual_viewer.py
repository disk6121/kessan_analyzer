
import streamlit as st

from utils.quarters_utils import process_to_8quarters


def render_quarter_actual_viewer(ticker,combined_data):

    if not combined_data:
        return

    with st.expander("🔍 四半期業績（単四半期実績）"):

        df = process_to_8quarters(combined_data)

        if df.empty:
            st.info("表示できるデータがありません。")
            return

        # 表示用に列名を変更
        df = df.rename(columns={
            "Period": "決算期",
            "Revenue": "売上高 (百万円)",
            "Income": "営業利益 (百万円)"
        })

        # 表示不要な列を削除
        df = df[[
            "決算期",
            "売上高 (百万円)",
            "営業利益 (百万円)"
        ]]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )