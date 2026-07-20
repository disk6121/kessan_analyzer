

import pandas as pd
import streamlit as st


def render_kpi_editor(stock_meta, combined_data):

    # -------------------------------
    # 四半期一覧
    # -------------------------------
    quarters = sorted(combined_data.keys())

    if len(quarters) == 0:
        st.info("四半期データがありません。")
        return stock_meta

    # -------------------------------
    # 保存済みデータ
    # -------------------------------
    kpi_data = stock_meta.get("kpi_data", {})

    # -------------------------------
    # KPI項目一覧を作成
    # -------------------------------
    default_items = [
        "受注残高",
        "受注高",
        "契約社数",
        "コンサルタント数",
        "その他"
    ]

    # 保存済みKPI名も取得
    saved_items = set(default_items)

    for quarter_data in kpi_data.values():
        if isinstance(quarter_data, dict):
            saved_items.update(quarter_data.keys())

    items = list(saved_items)

    # -------------------------------
    # DataFrame作成
    # -------------------------------
    rows = []

    for item in items:
    
        row = {"KPI": item}

        for q in quarters:
            row[q] = kpi_data.get(q, {}).get(item, None)

        rows.append(row)

    df = pd.DataFrame(rows)

    # -------------------------------
    # 編集
    # -------------------------------
    column_config = {
        "KPI": st.column_config.TextColumn(
            "KPI",
            required=True
        )
    }

    for q in quarters:
        column_config[q] = st.column_config.NumberColumn(
            q,
            format="%.1f"
        )

    edited_df = st.data_editor(
        df,
        hide_index=True,
        width="stretch",
        num_rows="dynamic",
        key="kpi_editor",
        column_config=column_config
    )


    # -------------------------------
    # 保存
    # -------------------------------
    if st.button(
        "💾 KPI保存",
        width="stretch",
        key="save_kpi"
    ):

        new_kpi = {}
    
        for q in quarters:

            new_kpi[q] = {}

            for _, row in edited_df.iterrows():

                item = str(row["KPI"]).strip()

                if item == "":
                    continue

                value = row[q]

                if pd.notna(value):
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        continue

                    # 整数ならintで保存
                    if value.is_integer():
                        value = int(value)

                    new_kpi[q][item] = value

        stock_meta["kpi_data"] = new_kpi

        st.success("KPIを保存しました。")

        # 画面再描画（任意）
        st.rerun()

    return stock_meta
