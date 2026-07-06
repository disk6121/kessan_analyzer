
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
def generate_content_with_retry(client, model, contents, config):
    return client.models.generate_content(model=model, contents=contents, config=config)


def investigate_topic(api_key,topic,company_name,ticker):

    prompt_map = {
            "事業概要": f"「{company_name}({ticker})」の主要セグメントとビジネスモデルをWeb上の最新公表資料に基づき1000字以内で客観的にまとめてください。",
            "増収減収要因": f"「{company_name}({ticker})」の最新決算における売上高の増収または減収の要因を1000字以内でまとめてください。",
            "増益減益要因": f"「{company_name}({ticker})」の最新決算における営業利益等の増益または減益の要因を1000字以内でまとめてください。"
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

