###作成途中


import streamlit as st

def initialize_session():
    if "current_analysis" not in st.session_state:
        st.session_state.current_analysis = None

    if "last_loaded_ticker" not in st.session_state:
        st.session_state.last_loaded_ticker = None    

    if "deep_dive_memo_input" not in st.session_state:
        st.session_state.deep_dive_memo_input = ""

    if "reports_dict" not in st.session_state:
        st.session_state.reports_dict = {} 



def reset_reports():
    st.session_state.reports_dict= {}
