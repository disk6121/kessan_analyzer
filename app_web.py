import os
import streamlit as st
import pandas as pd

from database.db import refresh_watchlist_prices_batch
from database.db import get_watchlist
from database.db import delete_company
from utils.get_alert_utils import get_alert_status
from database.save_repository import save_companies_memo
from database.save_repository import save_common_note
from database.save_repository import save_analysis_data
from database.load_repository import load_common_note
from views.peer_comparison import render_peer_comparison
from services.analysis_loader import restore_analysis_to_session
from services.analysis_loader import load_saved_reports_to_session
from services.gemini_service import investigate_topic
from services.gemini_service import investigate_custom_query
from services.analysis_manager import manage_analysis
from services.analysis_loader import prepare_analysis_for_view
from views.analysis_view import render_analysis_visuals

import json
import streamlit as st

# ---------------------------------------------------------
# タイトル
# ---------------------------------------------------------
st.set_page_config(page_title="決算分析アプリ", layout="wide")
st.title("📊 決算短信分析アプリ")
st.write("決算短信をアップロードすると自動で分析を行います。")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Gemini API Keyを入力してください", type="password")


# ---------------------------------------------------------
# 【構成１】ウォッチリスト（既存データ）
# ---------------------------------------------------------
st.subheader("🗂️ マイ投資ウォッチリスト（保存済み企業一覧）")

# 【1-1】株価更新ボタン
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 株価更新",width="stretch"):
        refresh_watchlist_prices_batch()
        st.success("株価を更新しました")
        st.rerun()

# 【1-2】ウォッチリストを表形式で表示
df_db = get_watchlist()### companiesテーブルを取得
df_db["alert_status"] = df_db.apply(get_alert_status,axis=1)###　最新の株価に基づき株価アラートを更新

if not df_db.empty:###　companiesテーブルの項目を日本語名に置き換えて表示
    df_display = df_db[
        [
            "ticker", 
            "company_name",
            "saved_date", 
            "current_price", 
            "investment_memo",
            "is_favorite", 
            "buy_target", 
            "sell_target",
            "alert_status"
        ]
    ].rename(columns={
        "ticker": "証券コード", "company_name": "企業名", "saved_date": "保存日", "current_price": "株価",
        "investment_memo": "投資メモ", "is_favorite": "⭐お気に入り", 
        "buy_target": "買いたい価格", "sell_target": "売りたい価格", "alert_status":"アラート"
    })

    edited_df = st.data_editor(###　表内の一部機能については編集可能
        df_display,
        column_config={
            "⭐お気に入り": st.column_config.CheckboxColumn(help="気になる銘柄をチェック"),
            "投資メモ":st.column_config.TextColumn(width="large"),
            },
        disabled=["証券コード", "企業名", "保存日", "株価"],
        width="stretch",
        key="editor"
    )


# 【1-3】ウォッチリストの修正保存ボタンと削除ボタン
    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        if st.button("📌 リストの変更（チェック・メモ）を保存する", width="stretch"):
            save_companies_memo(edited_df)
            st.success("リストの変更内容をSQLiteに保存しました！")
            st.rerun()

    with col_btn2:
        delete_options = {f"[{row['ticker']}] {row['company_name']}": row['ticker'] for _, row in df_db.iterrows()}
        target_to_delete = st.selectbox("🗑️ 削除する企業を選択", options=[None] + list(delete_options.keys()), index=0, label_visibility="collapsed")
   
        if target_to_delete:
            ticker_to_delete = delete_options[target_to_delete]
            if st.button(f"🚨 {ticker_to_delete} を完全に削除", type="primary", width="stretch"):
                delete_company(ticker_to_delete)
                st.success(f"🗑️ {ticker_to_delete} のデータを削除しました。")
                st.rerun()


# 【1-4】全体メモ欄
    with st.expander("📝 共通メモ"):
        if "common_note_editor" not in st.session_state:
            st.session_state.common_note_editor = load_common_note()

        st.text_area(
            "",
            height=180,
            key="common_note_editor"
        )

        if st.button("💾 メモを保存", key="save_common_note"):
            save_common_note(st.session_state.common_note_editor)
            st.success("保存しました")



# 【1-5】買いシグナル、売りシグナル銘柄の一覧表示
    with st.expander("🗂️ アラート点灯リスト"):

        buy_df = edited_df[(edited_df["アラート"] == "🟢買い")&(edited_df["⭐お気に入り"]==True)].copy()
        buy_df["乖離率(%)"] = (
            (buy_df["売りたい価格"] - buy_df["株価"])
            / buy_df["株価"]
            * 100
        ).round(1)
        buy_df = buy_df[["証券コード", "企業名", "株価", "売りたい価格", "乖離率(%)"]]

        sell_df = edited_df[(edited_df["アラート"] == "🔴売り")&(edited_df["⭐お気に入り"]==True)].copy()
        sell_df["乖離率(%)"] = (
            (sell_df["株価"] - sell_df["買いたい価格"])
            / sell_df["買いたい価格"]
            * 100
        ).round(1)

        sell_df = sell_df[["証券コード", "企業名", "株価", "買いたい価格", "乖離率(%)"]]

        buy_df = buy_df.sort_values("乖離率(%)",ascending=False)
        sell_df = sell_df.sort_values("乖離率(%)",ascending=False)

        threshold = st.slider("表示する最低乖離率（％）", min_value=0,max_value=100,value=40,step=5)

        buy_df = buy_df[buy_df["乖離率(%)"]>= threshold]
        sell_df = sell_df[sell_df["乖離率(%)"]>= threshold]

        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🟢 買いシグナル {len(buy_df)}件")
            st.dataframe(buy_df,width="stretch")

        with col2:
            st.warning(f"🔴 売りシグナル {len(sell_df)}件")
            st.dataframe(sell_df,width="stretch")


# 【1-6】過去の分析結果詳細の呼び出し
    st.write("#### 📂 過去の分析結果を呼び出す")
    
    input_ticker = st.text_input(
        "確認したい企業の証券コード（4桁）を入力してください", 
        max_chars=4, 
        placeholder="例: 7203"
    ).strip()

    if input_ticker:
        loaded = prepare_analysis_for_view(input_ticker)
        if loaded:
            restore_analysis_to_session(input_ticker,loaded)
            st.info(f"📁 データベースから過去データをロードしました。対象企業: {loaded["meta"]['company_name']} ({loaded["meta"]['ticker']}.T)")
            render_analysis_visuals(st.session_state.current_analysis["meta"],  st.session_state.current_analysis["combined"],  st.session_state.current_analysis["seg"])###　描画処理
        else:
            st.error(f"⚠️ 証券コード「{input_ticker}」の分析データはデータベースに見つかりませんでした。先に下のフォームからPDFを解析してください。")


# ---------------------------------------------------------
# 【構成２】分析エリア（新規解析）
# ---------------------------------------------------------

# 【2-1】新規の決算短信分析
    if not input_ticker:

        st.divider()
        st.subheader("📥 新しい決算短信PDFを解析する")
        uploaded_files = st.file_uploader("決算短信のPDFファイルを選択（複数可）", type=["pdf"], accept_multiple_files=True, key="new_uploader")

        if uploaded_files:
            if st.button("すべての決算をまとめて徹底分析", type="primary", key="analyze_btn"):

                analysis = manage_analysis(uploaded_files,api_key)

                st.session_state.current_analysis = analysis

                load_saved_reports_to_session(analysis["meta"]["ticker"])

if st.session_state.get("current_analysis"):
    analysis = st.session_state.current_analysis
 
    if "reports_dict" not in st.session_state:
        st.session_state.reports_dict = {}


    if analysis.get("source") == "pdf":
        render_analysis_visuals(analysis["meta"], analysis["combined"], analysis["seg"])


# 【2-2】AI定型調査     
    st.divider()
    st.subheader("🔍 Webリアルタイム深掘り調査")
   
    col_b1, col_b2, col_b3 = st.columns(3)
    clicked_topic = None
    if col_b1.button("🏢 事業概要を調査", width="stretch"): clicked_topic = "事業概要"
    if col_b2.button("📈 増収減収要因を調査", width="stretch"): clicked_topic = "増収減収要因"
    if col_b3.button("💰 増益減益要因を調査", width="stretch"): clicked_topic = "増益減益要因"

    comp = analysis["meta"]["company_name"]
    tic = analysis["meta"]["ticker"]

    if clicked_topic:
        result = investigate_topic(api_key,clicked_topic,comp,tic)
        st.session_state.reports_dict[clicked_topic] = result

# 【2-3】AI自由調査
    st.write("##### ✍️ 自由なテーマでGeminiに調査を依頼する")
    custom_query = st.text_input(
        label="調べたい内容を入力してください（例: 最新の株価材料や新製品の評判、競合他社との違いなど）",
        placeholder=f"例: {comp}の最近の対話型AIに関するプレスリリースや、市場での評価について教えてください。",
        key=f"custom_query_input_{tic}"
    )
   
    if st.button("🔍 自由記述でWebリアルタイム調査を実行", type="secondary", width="stretch"):
        result = investigate_custom_query(api_key, comp, tic, custom_query)
        st.session_state.reports_dict["自由カスタム調査"] = result

    # --- 調査結果の表示エリア ---
    has_any_report = False
    for label, report_content in st.session_state.reports_dict.items():
        if report_content:
            has_any_report = True
            st.write(f"##### 📝 【{label}】の調査結果")
            st.success(report_content)

# 【2-4】メモ欄
    st.write("##### ✍️ 調査メモ・考察（自由記述欄）")
    if "deep_dive_memo_input" not in st.session_state:
        st.session_state.deep_dive_memo_input = ""
   
    user_memo = st.text_area(
        label="深掘り調査やAIレポートを踏まえたメモをここに入力してください。企業データと一緒にウォッチリストに保存されます。",
        placeholder="例: バリュー株投資候補／グロース株投資候補／割高修正投資候補＿＿買い○○円、売り○○円",
        height=150,
        key="deep_dive_memo_input"
    )
    st.session_state.deep_dive_memo = user_memo


# 【2-5】同業他社比較欄
    st.write("##### ✍️ 同業他社比較")
    render_peer_comparison(tic=tic, comp=comp, analysis=analysis)


# 【2-6】分析結果を保存
    st.divider()
    st.write("#### 💾 この企業のデータをウォッチリストに保存しますか？")
    
    if st.button("🌟 この分析結果をデータベースに保存する", type="primary", width="stretch"):
        save_analysis_data(
            analysis,
            st.session_state.reports_dict,
            st.session_state.deep_dive_memo_input,
            st.session_state.peer_comparison_df
        )
 
        st.success(f"🎉 {analysis['meta']['company_name']} のデータを【統合保存】しました！")
        st.rerun() 
