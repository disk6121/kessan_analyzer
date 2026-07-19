
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


# ---------------------------------------------------------
# 
# ---------------------------------------------------------

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry=retry_if_exception_type(ServerError),
    reraise=True
)

COMMON_PROMPT = """
あなたは日本株を専門とするセルサイド証券会社のシニアアナリストです。

Web検索を活用し、企業の最新の公表情報を基に投資家向けの分析を行ってください。

【情報源】
・企業の公式IR資料、決算短信、決算説明資料、有価証券報告書、中期経営計画、統合報告書などの一次情報を最優先してください。
・不足する場合のみ、信頼できるニュース、業界レポート、公的機関の情報で補完してください。
・噂や未確認情報は使用しないでください。

【分析方針】
・事実と分析・考察を区別してください。
・一般論ではなく、この企業固有の内容を中心に分析してください。
・公表資料から確認できない事項は推測せず、「公表資料からは確認できない」と記載してください。
・強みだけでなく、課題やリスクもバランスよく記載してください。
・単なる情報の羅列ではなく、投資家が理解しやすいよう整理・要約してください。

【文章】
・1000字以内でまとめてください。
・適宜見出しや箇条書きを用いて読みやすくしてください。
・専門用語には必要に応じて簡単な説明を添えてください。
・冗長な表現は避け、簡潔かつ客観的に記載してください。
"""

def generate_content_with_retry(client, model, contents, config):
    return client.models.generate_content(model=model, contents=contents, config=config)


def investigate_topic(api_key,topic,company_name,ticker):

    prompt_map = {
            "事業概要": f"「{company_name}({ticker})」の主要セグメントとビジネスモデルをWeb上の最新公表資料に基づき1000字以内で客観的にまとめてください。",
            "増収減収要因": f"「{company_name}({ticker})」の最新決算における売上高の増収または減収の要因を1000字以内でまとめてください。",
            "増益減益要因": f"「{company_name}({ticker})」の最新決算における営業利益等の増益または減益の要因を1000字以内でまとめてください。"
        }
    
    prompt_map = {

        "事業概要": f"""
    {COMMON_PROMPT}

    【調査テーマ】
    「{company_name}（{ticker}）」の事業概要

    以下の観点を含めて分析してください。

    ・主要事業・主要セグメント
    ・ビジネスモデル
    ・収益源
    ・顧客層
    ・事業の特徴
    ・利益を牽引している事業

    単なる会社紹介ではなく、投資家が事業構造を理解できる内容にしてください。
    """,

        "増収減収要因": f"""
    {COMMON_PROMPT}

    【調査テーマ】
    「{company_name}（{ticker}）」の最新決算における売上高の増減要因

    以下を分析してください。

    ・主要な増収・減収要因
    ・寄与したセグメント
    ・一時的要因か構造的要因か
    ・来期以降も継続する可能性
    ・投資家が注目すべきポイント
    """,

        "増益減益要因": f"""
    {COMMON_PROMPT}

    【調査テーマ】
    「{company_name}（{ticker}）」の最新決算における営業利益（必要に応じて経常利益・純利益）の増益（または減益）要因

    以下を含めてください。
    
    ・利益増減の主な要因
    ・利益率改善・悪化要因
    ・コスト構造の変化
    ・一時的要因か継続的要因か
    ・今後利益率が改善・悪化する可能性
    """,

        "競争優位性": f"""
    {COMMON_PROMPT}

    【調査テーマ】
    「{company_name}（{ticker}）」の競争優位性

    以下を含めてください。
    
    ・競争優位性の源泉
    ・他社との差別化要因
    ・参入障壁
    ・競争優位が持続する理由
    ・競争優位を脅かす要因

    最後に、競争優位性を総合評価してください。
    """,

        "成長戦略": f"""
    {COMMON_PROMPT}

    【調査テーマ】
    「{company_name}（{ticker}）」の成長戦略

    以下を含めてください。
    
    ・中期経営計画
    ・重点投資分野
    ・新規事業
    ・海外展開
    ・M&A戦略
    ・今後3〜5年の成長ドライバー

    最後に、成長戦略の実現可能性について評価してください。
    """,        

        "市場環境": f"""
    {COMMON_PROMPT}

    【調査テーマ】
    「{company_name}（{ticker}）」が属する市場・業界

    以下を含めてください。
    
    ・市場規模
    ・市場成長率
    ・業界トレンド
    ・競争環境
    ・今後市場が拡大・縮小すると考えられる理由
    ・企業にとって追い風・逆風となる外部環境

    最後に、市場環境が今後の業績へ与える影響をまとめてください。
    """,          
        
        "事業リスク": f"""
    {COMMON_PROMPT}

    【調査テーマ】
    「{company_name}（{ticker}）」の事業リスク

    以下を含めてください。
    
    ・業績下振れ要因
    ・競争激化リスク
    ・市場環境の変化
    ・法規制リスク
    ・為替・原材料価格など外部要因
    ・人材・採用リスク
    ・特定顧客・地域への依存リスク

    最後に、『今後最も注意すべきリスク』を3つ挙げてください。
    """,                

        
        "重要KPI": f"""
    {COMMON_PROMPT}

    【調査テーマ】
    「{company_name}（{ticker}）」の重要KPI

    以下を含めてください。
    
    ・重要KPIを3〜5個
    ・各KPIが重要な理由
    ・次回決算で確認すべきポイント
    ・KPIが改善した場合に期待できること
    ・悪化した場合の影響

    投資家が決算を見る際のチェックリストとして活用できる内容にしてください。
    """                      
}


    
    with st.spinner(f"🌐 Google検索連携で{topic}をリアルタイム調査中..."):
        client = genai.Client(api_key=api_key)
        res = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_map[topic],
            config=types.GenerateContentConfig(tools=[{"google_search": {}}])
        )
    return res.text




def investigate_custom_query(api_key,company_name,ticker,custom_query):
    if not custom_query.strip():
        st.warning("⚠️ 調査したい内容を入力してください。")
    else:
        full_prompt = f"対象企業: {company_name} ({ticker}.T)\n\n調査指示: {custom_query}\n\nWeb上の最新情報をGoogle検索を活用して調査し、分かりやすくまとめてください。"
           
        with st.spinner(f"🌐 Google検索連携で『{custom_query[:20]}...』をリアルタイム調査中..."):
            try:
                client = genai.Client(api_key=api_key)
                res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=full_prompt,
                    config=types.GenerateContentConfig(tools=[{"google_search": {}}])
                )
                return res.text

            except Exception as e:
                st.error(f"❌ 調査中にエラーが発生しました: {e}")

