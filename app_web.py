import os
import streamlit as st
import pandas as pd
import json

from decimal import Decimal, ROUND_HALF_UP
from database.db import refresh_watchlist_prices_batch
from database.db import get_watchlist
from database.db import delete_company
from utils.get_alert_utils import get_alert_status
from database.save_repository import save_companies_memo
from database.save_repository import save_common_note
from database.save_repository import save_analysis_data
from database.load_repository import load_common_note
from views.peer_comparison import render_peer_comparison
from views.investment_report import render_investment_report
from services.analysis_loader import restore_analysis_to_session
from services.analysis_loader import load_saved_reports_to_session
from services.gemini_service import investigate_topic
from services.gemini_service import investigate_custom_query
from services.analysis_manager import manage_analysis
from services.analysis_loader import prepare_analysis_for_view
from services.investment_report import generate_investment_report
from services.calc_expectation_service import calc_expectation
from services.announcement_service import get_company_schedule
from services.announcement_service import get_schedule_dict
from services.announcement_service import get_days_until_announcement
from services.announcement_service import get_days_diff
from views.analysis_view import render_analysis_visuals


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

def calculate_target_price(eps, assumed_per):
    """想定EPS × 想定PERを四捨五入して目標株価を計算"""

    if eps is None or assumed_per is None:
        return None

    try:
        value = Decimal(str(eps)) * Decimal(str(assumed_per))

        return int(
            value.quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP
            )
        )

    except Exception:
        return None


# 【1-2】ウォッチリストを表形式で表示
df_db = get_watchlist()

# 保存日の新しい順に並べ替え
df_db["saved_date"] = pd.to_datetime(
    df_db["saved_date"],
    format="mixed",
    errors="coerce",
    utc=True
)

df_db = df_db.sort_values(
    "saved_date",
    ascending=False
).reset_index(drop=True)

df_db["saved_date"] = df_db["saved_date"].dt.tz_convert("Asia/Tokyo")

# 決算予定情報
schedule_dict = get_schedule_dict("kessan_schedule.xlsx")

df_db["schedule"] = df_db["ticker"].apply(
    lambda x: get_company_schedule(x, schedule_dict)
)

df_db["announcement_date"] = df_db["schedule"].apply(
    lambda x: x["announcement_date"] if x else pd.NaT
)

df_db["announcement_type"] = df_db["schedule"].apply(
    lambda x: x["announcement_type"] if x else ""
)

df_db["days_until"] = df_db["announcement_date"].apply(
    get_days_until_announcement
)

df_db["announcement_display"] = df_db.apply(
    lambda row:
        f'{row["announcement_date"].strftime("%Y/%m/%d")} ({row["days_until"]})'
        if pd.notna(row["announcement_date"])
        else "",
    axis=1
)

df_db["days_diff"] = df_db["announcement_date"].apply(
    get_days_diff
)

df_db["expectation"] = df_db.apply(
    calc_expectation,
    axis=1
)


if not df_db.empty:

    df_db["is_favorite"] = df_db["is_favorite"].fillna(False)
    df_db["is_short_term"] = df_db["is_short_term"].fillna(False)

    df_db["assumed_eps"] = pd.to_numeric(df_db["assumed_eps"],errors="coerce")
    
    df_db["assumed_per"] = pd.to_numeric(
        df_db["assumed_per"],
        errors="coerce"
    )

    df_db["target_price"] = df_db.apply(
        lambda row: calculate_target_price(
            row["assumed_eps"],
            row["assumed_per"]
        ),
        axis=1
    )

    # 表示用DataFrame
    df_display = df_db[
        [
            "ticker",
            "company_name",
            "investment_memo",
            "saved_date",
            "current_price",
            "is_favorite",
            "is_short_term",
            "evaluation",
            "assumed_per",
            "assumed_eps",
            "target_price",
            "expectation"
        ]
    ].rename(columns={
        "ticker": "証券コード",
        "company_name": "企業名",
        "investment_memo": "投資メモ",
        "saved_date": "保存日",
        "current_price": "株価",
        "is_favorite": "長期投資候補",
        "is_short_term": "短期投資候補",
        "evaluation": "評価",
        "assumed_per": "想定PER",
        "assumed_eps": "想定EPS",
        "target_price": "目標株価",
        "expectation": "決算期待度(%)"
    })

    df_display["保存日"] = df_display["保存日"].dt.strftime(
        "%Y-%-m-%-d %H:%M"
    )

    edited_df = st.data_editor(
        df_display,

        column_config={
            "長期投資候補": st.column_config.CheckboxColumn(
                help="長期投資候補として登録"
            ),

            "短期投資候補": st.column_config.CheckboxColumn(
                help="短期投資候補として登録"
            ),

            "投資メモ": st.column_config.TextColumn(
                width="large"
            ),

            "評価": st.column_config.TextColumn(
                help="企業の評価を自由に入力"
            ),

            "想定PER": st.column_config.NumberColumn(
                help="想定するPERを入力",
                format="%.1f"
            ),

            "想定EPS": st.column_config.NumberColumn(
                format="%.1f"
            ),

            "目標株価": st.column_config.NumberColumn(
                format="%d"
            )
        },

        disabled=[
            "証券コード",
            "企業名",
            "保存日",
            "株価",
            "想定EPS",
            "目標株価",
            "決算期待度(%)"
        ],

        width="stretch",
        key="editor_v2"
    )

    

# 【1-3】ウォッチリストの修正保存ボタンと削除ボタン
    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        if st.button("📌 リストの変更（チェック・メモ）を保存する", width="stretch"):
            save_companies_memo(edited_df)
            st.success("リストの変更内容をSupabaseに保存しました！")
            st.rerun()

        if st.button("📌 リストの変更（候補・評価・PER・メモ）を保存する", width="stretch"):
            save_companies_memo(edited_df)
            st.success("リストの変更内容をSupabaseに保存しました！")
            st.rerun()

    
    with col_btn2:
        # st.markdown("🗑️ **削除する企業**")
        # 証券コードを手入力
        delete_ticker_input = st.text_input(
            "証券コード",
            placeholder="削除する企業の証券コードを入力　例：7203",
            label_visibility="collapsed",
            key="delete_ticker_input"
        )
        if delete_ticker_input:
            # 前後の空白を削除
            ticker_to_delete = delete_ticker_input.strip().upper()
            # 入力された証券コードに一致する企業を検索
            matched = df_db[
                df_db["ticker"].astype(str).str.upper() == ticker_to_delete
            ]

            if len(matched) == 0:

                st.warning(
                    f"証券コード「{ticker_to_delete}」の企業は"
                    "ウォッチリストにありません。"
                )

            else:
                company_name = matched.iloc[0]["company_name"]
    
                st.warning(
                    f"⚠️ **{company_name}** のデータを削除しますか？"
                )

                if st.button(
                    f"🚨 {ticker_to_delete} を完全に削除",
                    type="primary",
                    width="stretch",
                    key="delete_company_button"
                ):
                    delete_company(ticker_to_delete)

                    st.success(
                        f"🗑️ [{ticker_to_delete}] "
                        f"{company_name} のデータを削除しました。"
                    )

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


# 【1-5】アラート点灯リスト
    with st.expander("🗂️ アラート点灯リスト"):

        threshold = st.slider(
            "参考銘柄に表示する最低乖離率（％）",
            min_value=0,
            max_value=100,
            value=50,
            step=5
        )

        alert_data = edited_df.copy()

        # チェックボックスの欠損値対策
        for col in ["長期投資候補", "短期投資候補"]:
            alert_data[col] = (
                alert_data[col].fillna(False).astype(bool)
            )

        # 数値型に変換
        for col in ["株価", "目標株価"]:
            alert_data[col] = pd.to_numeric(
                alert_data[col],
                errors="coerce"
            )
    
        # 目標株価と現在株価の乖離率
        # （目標株価 - 現在株価）÷ 現在株価 × 100
        alert_data["乖離率(%)"] = (
            (
                alert_data["目標株価"] - alert_data["株価"]
            )
            / alert_data["株価"].where(alert_data["株価"] > 0)
            * 100
        )

        # 共通表示列
        display_cols = [
            "証券コード",
            "企業名",
            "投資メモ",
            "乖離率(%)",
            "決算期待度(%)"
        ]

        # 表示用の乖離率は小数第1位まで
        alert_data["乖離率(%)"] = alert_data["乖離率(%)"].round(1)

        # =====================================================
        # ① 買いシグナル（短期）
        # 株価 < 目標株価 ＋ 短期候補ON
        # =====================================================
        buy_short_df = alert_data[
            (alert_data["株価"] < alert_data["目標株価"])
            & (alert_data["短期投資候補"])
        ].copy()

        buy_short_df = buy_short_df.sort_values(
            "乖離率(%)",
            ascending=False,
            na_position="last"
        )[display_cols]

        # =====================================================
        # ② 売りシグナル（短期）
        # 株価 > 目標株価 ＋ 短期候補ON
        # =====================================================
        sell_short_df = alert_data[
            (alert_data["株価"] > alert_data["目標株価"])
            & (alert_data["短期投資候補"])
        ].copy()

        sell_short_df = sell_short_df.sort_values(
            "乖離率(%)",
            ascending=True,
            na_position="last"
        )[display_cols]

    # =====================================================
    # ③ 買いシグナル（長期）
    # 株価 < 目標株価 ＋ 長期候補ON
    # =====================================================
        buy_long_df = alert_data[
            (alert_data["株価"] < alert_data["目標株価"])
            & (alert_data["長期投資候補"])
        ].copy()

        buy_long_df = buy_long_df.sort_values(
            "乖離率(%)",
            ascending=False,
            na_position="last"
        )[display_cols]

    # =====================================================
    # ④ 参考銘柄（割安）
    # 長期・短期候補OFF ＋ 乖離率 > 閾値
    # =====================================================
        no_candidate = (
            (~alert_data["長期投資候補"])
            & (~alert_data["短期投資候補"])
        )

        reference_cheap_df = alert_data[
            no_candidate
            & (alert_data["乖離率(%)"] > threshold)
        ].copy()

        reference_cheap_df = reference_cheap_df.sort_values(
            "乖離率(%)",
            ascending=False,
            na_position="last"
        )[display_cols]

    # =====================================================
    # ⑤ 参考銘柄（割高）
    # 長期・短期候補OFF ＋ 乖離率 × -1 > 閾値
    # =====================================================
        reference_expensive_df = alert_data[
            no_candidate
            & (alert_data["乖離率(%)"] * -1 > threshold)
        ].copy()

        reference_expensive_df = reference_expensive_df.sort_values(
            "乖離率(%)",
            ascending=True,
            na_position="last"
        )[display_cols]

    # =====================================================
    # 5つのリストを表示
    # =====================================================

        col1, col2 = st.columns(2)

        with col1:
            st.success(
                f"🟢 買いシグナル（短期） {len(buy_short_df)}件"
            )
            st.dataframe(
                buy_short_df,
                width="stretch",
                hide_index=True
            )

        with col2:
            st.warning(
                f"🔴 売りシグナル（短期） {len(sell_short_df)}件"
            )
            st.dataframe(
                sell_short_df,
                width="stretch",
                hide_index=True
            )

        col3, col4 = st.columns(2)

        with col3:
            st.info(
                f"🟢 買いシグナル（長期） {len(buy_long_df)}件"
            )
            st.dataframe(
                buy_long_df,
                width="stretch",
                hide_index=True
            )

        with col4:
            st.info(
                f"📈 参考銘柄（割安） {len(reference_cheap_df)}件"
            )
            st.dataframe(
                reference_cheap_df,
                width="stretch",
                hide_index=True
            )

        st.info(
            f"📉 参考銘柄（割高） {len(reference_expensive_df)}件"
        )
        st.dataframe(
            reference_expensive_df,
            width="stretch",
            hide_index=True
        )


    
# 【1-6】決算発表スケジュール
    with st.expander("📅 決算発表スケジュール"):
        today_df = df_db[df_db["days_diff"] == 0]
        today_df = today_df[["ticker", "company_name", "is_favorite", "expectation"]].rename(columns={
            "ticker": "証券コード", "company_name": "企業名", "is_favorite": "⭐お気に入り", "expectation": "決算期待度(%)"
            })
        
        upcoming_df = df_db[(df_db["days_diff"] >= 1)&(df_db["days_diff"] <= 7)].sort_values("days_diff")
        upcoming_df = upcoming_df[["ticker", "company_name", "is_favorite", "announcement_display", "expectation"]].rename(columns={
            "ticker": "証券コード", "company_name": "企業名", "is_favorite": "⭐お気に入り", "announcement_display": "決算予定",  "expectation": "決算期待度(%)"
            })
        
        recent_df = df_db[(df_db["days_diff"] >= -7)&(df_db["days_diff"] <= -1)].sort_values("days_diff", ascending=False)
        recent_df = recent_df[["ticker", "company_name", "is_favorite", "announcement_display", "expectation"]].rename(columns={
            "ticker": "証券コード", "company_name": "企業名", "is_favorite": "⭐お気に入り", "announcement_display": "決算予定",  "expectation": "決算期待度(%)"
            })

        
        col1, col2, col3 = st.columns(3)
        with col1:
            if not today_df.empty:
                st.success("🔴 今日発表")
                st.dataframe(today_df,hide_index=True)
        with col2:
            if not upcoming_df.empty:
                st.warning("🟠 7日以内に発表予定")
                st.dataframe(upcoming_df,hide_index=True,width="stretch")
        with col3:
            if not recent_df.empty:
                st.info("🟢 過去7日以内に発表")
                st.dataframe(recent_df,hide_index=True)


# 【1-6】決算発表スケジュール
    with st.expander("📅 決算発表スケジュール"):

        today_df = df_db[df_db["days_diff"] == 0]

        today_df = today_df[
            [
                "ticker",
                "company_name",
                "is_favorite",
                "is_short_term",
                "expectation"
            ]
        ].rename(columns={
            "ticker": "証券コード",
            "company_name": "企業名",
            "is_favorite": "長期投資候補",
            "is_short_term": "短期投資候補",
            "expectation": "決算期待度(%)"
        })

        upcoming_df = df_db[
            (df_db["days_diff"] >= 1)
            & (df_db["days_diff"] <= 7)
        ].sort_values("days_diff")

        upcoming_df = upcoming_df[
            [
                "ticker",
                "company_name",
                "is_favorite",
                "is_short_term",
                "announcement_display",
                "expectation"
            ]
        ].rename(columns={
            "ticker": "証券コード",
            "company_name": "企業名",
            "is_favorite": "長期投資候補",
            "is_short_term": "短期投資候補",
            "announcement_display": "決算予定",
            "expectation": "決算期待度(%)"
        })

        recent_df = df_db[
            (df_db["days_diff"] >= -7)
            & (df_db["days_diff"] <= -1)
        ].sort_values("days_diff", ascending=False)

        recent_df = recent_df[
            [
                "ticker",
                "company_name",
                "is_favorite",
                "is_short_term",
                "announcement_display",
                "expectation"
            ]
        ].rename(columns={
            "ticker": "証券コード",
            "company_name": "企業名",
            "is_favorite": "長期投資候補",
            "is_short_term": "短期投資候補",
            "announcement_display": "決算予定",
            "expectation": "決算期待度(%)"
        })

        col1, col2, col3 = st.columns(3)

        with col1:
            if not today_df.empty:
                st.success("🔴 今日発表")
                st.dataframe(
                    today_df,
                    hide_index=True,
                    width="stretch"
                )

        with col2:
            if not upcoming_df.empty:
                st.warning("🟠 7日以内に発表予定")
                st.dataframe(
                    upcoming_df,
                    hide_index=True,
                    width="stretch"
                )

        with col3:
            if not recent_df.empty:
                st.info("🟢 過去7日以内に発表")
                st.dataframe(
                    recent_df,
                    hide_index=True,
                    width="stretch"
                )
    
    
# 【1-7】過去の分析結果詳細の呼び出し
    st.write("#### 📂 過去の分析結果を呼び出す")

    # --------------------------------------------------------
    # 同業他社比較から会社を切り替え
    # --------------------------------------------------------
    if "selected_ticker" in st.session_state:
        ticker = st.session_state.pop("selected_ticker")
        st.session_state.input_ticker = ticker
        analysis = prepare_analysis_for_view(ticker)
        if analysis is not None:
            restore_analysis_to_session(ticker,analysis)
            st.session_state.current_analysis = analysis
    
    input_ticker = st.text_input(
        "確認したい企業の証券コード（4桁）を入力してください", 
        key="input_ticker",
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
    with st.expander("🔍 Webリアルタイム深掘り調査"):
   
        col_b1, col_b2 = st.columns(2)
        col_b3, col_b4 = st.columns(2)
        col_b5, col_b6 = st.columns(2)
        col_b7, col_b8 = st.columns(2)
        clicked_topic = None
        if col_b1.button("🏢 事業概要", width="stretch"): clicked_topic = "事業概要"
        if col_b2.button("📈 増収減収要因", width="stretch"): clicked_topic = "増収減収要因"
        if col_b3.button("💰 増益減益要因", width="stretch"): clicked_topic = "増益減益要因"
        if col_b4.button("🏆 競争優位性", width="stretch"): clicked_topic = "競争優位性"
        if col_b5.button("🚀 成長戦略", width="stretch"): clicked_topic = "成長戦略"
        if col_b6.button("🌏 市場環境", width="stretch"): clicked_topic = "市場環境"
        if col_b7.button("⚠️ 事業リスク", width="stretch"): clicked_topic = "事業リスク"
        if col_b8.button("📊 重要KPI", width="stretch"): clicked_topic = "重要KPI"
    
        comp = analysis["meta"]["company_name"]
        tic = analysis["meta"]["ticker"]

        if clicked_topic:
            result = investigate_topic(api_key, clicked_topic,comp,tic)
            st.session_state.reports_dict[clicked_topic] = result

# 【2-3】AI自由調査

        custom_query = st.text_input(
            label="自由記述調査",
            placeholder=f"例: {comp}の最近の対話型AIに関するプレスリリースや、市場での評価について教えてください。",
            key=f"custom_query_input_{tic}"
        )
   
        if st.button("🔍 自由記述でWebリアルタイム調査を実行", type="secondary", width="stretch"):
            result = investigate_custom_query(api_key, comp, tic, custom_query)
            st.session_state.reports_dict["自由カスタム調査"] = result

        # --- 調査結果の表示エリア ---
        st.divider()
        has_any_report = False
        for label, report_content in st.session_state.reports_dict.items():
            if report_content:
                has_any_report = True
                st.write(f"##### 📝 【{label}】の調査結果")
                st.success(report_content)


# 【2-4】同業他社比較欄
    with st.expander("✍️ 同業他社比較"):
        render_peer_comparison(tic=tic, comp=comp, analysis=analysis)


# 【2-5】AIレポート欄
#    st.write("##### ✍️ AIレポート")
#    col1, col2 = st.columns([1, 4])
#    with col1:
#        if st.button("🌟 この分析結果をもとにAIレポートを作成する", width="stretch"):
#            report = generate_investment_report(api_key,tic)
#            render_investment_report(report)
    
    
# 【2-6】メモ欄
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


    

# 【2-7】分析結果を保存
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
