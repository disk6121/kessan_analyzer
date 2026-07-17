import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from utils.chart_utils import draw_growth_arrow
from utils.quarters_utils import process_to_8quarters

from matplotlib import font_manager
import matplotlib.pyplot as plt
from pathlib import Path

def render_quarter_chart(combined_data,kpi_data=None,selected_kpi=None):

    font_path = Path(__file__).resolve().parent.parent / "fonts" / "NotoSansJP-VariableFont_wght.ttf"
    font_manager.fontManager.addfont(str(font_path))
    plt.rcParams["font.family"] = "Noto Sans JP"
    plt.rcParams["axes.unicode_minus"] = False
    
    st.divider()
    df_8q = process_to_8quarters(combined_data)
    if not df_8q.empty:
        df_8q_clean = df_8q.dropna(subset=["Revenue", "Income"], how="all").reset_index(drop=True)
    else:
        df_8q_clean = pd.DataFrame()

    if not df_8q_clean.empty:
        st.subheader("📈 業績トレンド分析（単四半期 連続推移）")
        plt.rcParams["font.family"] = "Noto Sans JP"
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5))
   
        # 売上グラフ
        ax1.bar(df_8q_clean["Period"], df_8q_clean["Revenue"], color="royalblue", alpha=0.8, width=0.5, label="売上高")

        # -----------------------
        # KPI折れ線
        # -----------------------
        if kpi_data and selected_kpi:
            kpi_values = []
            for quarter in df_8q_clean["QuarterKey"]:
                kpi_values.append(
                    kpi_data.get(quarter, {}).get(selected_kpi)
                )
            ax1_twin = ax1.twinx()
            ax1_twin.plot(
                df_8q_clean["Period"],
                kpi_values,
                color="crimson",
                marker="o",
                linewidth=2,
                label=selected_kpi
            )
            ax1_twin.set_ylabel(selected_kpi)
        
        ax1.set_title("単四半期 売上高の推移", weight='bold')
        ax1.grid(axis='y', linestyle='--')
        latest_idx = len(df_8q_clean) - 1
        if latest_idx >= 0:
            max_val = df_8q_clean["Revenue"].max() or 1
            if latest_idx - 1 >= 0:
                draw_growth_arrow(ax1, df_8q_clean, latest_idx, latest_idx - 1, "前四半期比", "darkorange", max_val * 0.05)
            if latest_idx - 4 >= 0:
                draw_growth_arrow(ax1, df_8q_clean, latest_idx, latest_idx - 4, "前年同期比", "crimson", max_val * 0.1)

        # 利益グラフ
        df_8q_clean["Margin(%)"] = (df_8q_clean["Income"] / df_8q_clean["Revenue"] * 100).round(2)
        ax2.bar(df_8q_clean["Period"], df_8q_clean["Income"], color="orange", alpha=0.8, width=0.5, label="営業利益")
        ax2.set_title("単四半期 営業利益率の推移", weight='bold')
        ax2.grid(axis='y', linestyle='--')
        ax2_twin = ax2.twinx()
        ax2_twin.plot(df_8q_clean["Period"], df_8q_clean["Margin(%)"], color="crimson", marker="o", lw=2, label="営業利益率")
        st.pyplot(fig)
