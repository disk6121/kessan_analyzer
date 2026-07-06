import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


def render_segment_analysis(df_pivot_rev,df_pivot_prof):

    if df_pivot_rev is None or df_pivot_prof is None:
        st.info("※解析されたセグメントの時系列データが空のため、表示をスキップします。")
        return

    if (df_pivot_rev.sum().sum() == 0) or (df_pivot_prof.sum().sum() == 0):
            st.info("※セグメント別の数値データがまだ十分に蓄積されていないため、セグメントグラフをスキップします。")

    st.divider()
    st.subheader("🧩 報告セグメント別 単四半期推移分析（時系列）")

    fig_seg, (ax_seg1, ax_seg2) = plt.subplots(1, 2, figsize=(16, 5))
    df_pivot_rev.plot(kind="bar", ax=ax_seg1, cmap="tab10", width=0.7)
    ax_seg1.set_title("セグメント別 売上高推移 (8期連続)", weight='bold')
    ax_seg1.set_ylabel("売上高（百万円）")
    ax_seg1.set_xticklabels(ax_seg1.get_xticklabels(), rotation=0)
               
    df_pivot_prof.plot(kind="bar", ax=ax_seg2, cmap="tab10", width=0.7)
    ax_seg2.set_title("セグメント別 利益推移 (8期連続)", weight='bold')
    ax_seg2.set_ylabel("セグメント利益（百万円）")
    ax_seg2.set_xticklabels(ax_seg2.get_xticklabels(), rotation=0)
    plt.tight_layout()
    st.pyplot(fig_seg)
