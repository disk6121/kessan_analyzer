

import json
from google import genai
from google.genai import types
from datetime import datetime
from database.load_repository import load_analysis_data
from database.load_repository import load_json


def generate_investment_report(api_key,ticker):

    row_data, meta_row = load_analysis_data(ticker)   
    
    combined_data = load_json(row_data["combined_data_json"])
    annual_performance = load_json(meta_row["annual_perf_json"]) 
    financial_meta = load_json(meta_row["financial_meta_json"]) 
    segment_analysis = load_json(row_data["seg_data_json"])
    peer_comparison = []
    if row_data.get("peer_comparison_json"):    
        peer_comparison = load_json(row_data["peer_comparison_json"])
    deep_dive_reports = load_json(row_data["ai_deep_dive_json"])
    kpi = {}
    if meta_row.get("kpi_json"):
        kpi = load_json(meta_row["kpi_json"])
    
    client = genai.Client(api_key=api_key)

    prompt = f"""
  あなたは日本株を専門とするセルサイド証券会社のシニアアナリストです。
  以下の企業分析データを基に、個人投資家向けの投資判断レポートを作成してください。

  ## レポートの目的
  本レポートは、決算内容・財務状況・事業内容・競争環境などを総合的に分析し、中長期投資の判断材料を提供することを目的とします。
  単なる情報の要約ではなく、
  ・企業の強み
  ・課題
  ・今後の成長性
  ・投資判断上のリスク
  まで踏み込んで分析してください。

  =========================
  【入力データ】
  =========================

  ■ 四半期業績
  {json.dumps(combined_data, ensure_ascii=False, indent=2)}

  ■ 通期業績
  {json.dumps(annual_performance, ensure_ascii=False, indent=2)}

  ■ 財務情報
  {json.dumps(financial_meta, ensure_ascii=False, indent=2)}

  ■ セグメント分析
  {json.dumps(segment_analysis, ensure_ascii=False, indent=2)}

  ■ 同業比較
  {json.dumps(peer_comparison, ensure_ascii=False, indent=2)}

  ■ AI深掘り分析
  {json.dumps(deep_dive_reports, ensure_ascii=False, indent=2)}

  ■ KPI
  {json.dumps(kpi, ensure_ascii=False, indent=2)}

  =========================
  【分析方針】
  =========================

  以下のルールを必ず守ってください。

  ・入力データを根拠に分析してください。
  ・一般論ではなく、この企業固有の内容を書いてください。
  ・数値がある場合は積極的に引用してください。
  ・ポジティブ・ネガティブ双方を書いてください。
  ・同じ内容を複数の項目で繰り返さないでください。
  ・入力データから判断できないことは推測しないでください。
  ・「買い」「売り」などの投資推奨は行わないでください。
  ・専門用語は必要に応じて簡単に説明してください。

  =========================
  【出力形式】
  =========================

  必ずJSONのみ返してください。

  {{
    "growth": {
      "title": "成長性",
      "comment": "",
      "positive_points": [],
      "concerns": [],
      "growth_drivers": [],
      "watch_points": []
    },

    "profitability": {
      "title": "収益性",
      "comment": "",
      "positive_points": [],
      "concerns": [],
      "watch_points": []
    },

    "financial_health": {
      "title": "財務健全性",
      "comment": "",
      "positive_points": [],
      "concerns": [],
      "watch_points": []
    },

    "valuation": {
      "title": "バリュエーション",
      "comment": "",
      "positive_points": [],
      "concerns": [],
      "watch_points": []
    },

    "investment_risks": {
      "business_risks": [],
      "financial_risks": [],
      "market_risks": []
    },

    "investment_scenario": {
      "bull_case": "",
      "bear_case": "",
      "key_monitoring_points": []
    },

    "next_quarter_focus": [],

    "investment_view": {
      "stance": "",
      "reason": "",
      "generated_at": ""
    },

    "summary": ""
  }}

  =========================
  【各項目の作成ルール】
  =========================

  ■ growth
  ・売上・利益・EPSの成長性を評価してください。
  ・今後の成長ドライバーを整理してください。
  ・次回決算で確認すべきポイントを書いてください。

  ■ profitability
  ・営業利益率など収益性を評価してください。
  ・利益率改善・悪化要因を書いてください。

  ■ financial_health
  ・自己資本比率
  ・営業CF
  ・有利子負債
  ・キャッシュ
  を総合的に評価してください。

  ■ valuation
  ・PER
  ・PBR
  ・配当利回り
  ・同業比較
  を基に評価してください。

  ■ investment_risks
  以下に分類してください。
  ・業績下振れ要因
  ・財務リスク
  ・株価リスク

  ■ investment_scenario
  bull_case
  今後株価上昇につながるシナリオ

  bear_case
  投資判断を見直すべきシナリオ

  key_monitoring_points
  投資家が最重要視すべきKPI

  ■ next_quarter_focus
  次回決算で最優先に確認すべき項目を5項目以内でまとめてください。

  ■ investment_view
  以下から最も近いものを選択してください。
  ・非常に注目
  ・注目
  ・中立
  ・慎重
  ・非常に慎重
  reasonには100〜200字程度で理由を書いてください。

  ■ summary
  200〜300字でレポート全体を要約してください。

  """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json"
        )
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()
    try:
        report = json.loads(text)
    except json.JSONDecodeError:
        report = {
            "error": "JSONの解析に失敗しました。",
            "raw_text": text
        }

    report["investment_view"]["generated_at"] = (
        datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    return report


