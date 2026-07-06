
import streamlit as st
import matplotlib.pyplot as plt

def render_segment_viewer(df_pivot_rev, df_pivot_prof):

    with st.expander("🔍 セグメント別単四半期売上・利益"):
        st.write("##### 🔹 セグメント別 単四半期売上高 (百万円)")
        st.dataframe(df_pivot_rev, use_container_width=True)
        st.write("##### 🔹 セグメント別 単四半期利益 (百万円)")
        st.dataframe(df_pivot_prof, use_container_width=True)

