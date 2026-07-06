import sqlite3
import pandas as pd
import numpy as np
import json
from datetime import datetime

from database.supabase_client import supabase

# SQLiteデータベース
SQLITE_DB = "investment_db.sqlite"


JSON_COLUMNS = {
    "companies": [
        "financial_meta_json",
        "annual_perf_json",
        "user_forecast_json",
    ],
    "initial_data": [
        "combined_data_json",
        "seg_data_json",
        "ai_deep_dive_json",
        "peer_comparison_json",
    ],
    "app_settings": [],
}


CONFLICT_KEYS = {
    "companies": "ticker",
    "initial_data": "ticker",
    "app_settings": "setting_key",
}


def clean_value(value):

    # None
    if value is None:
        return None

    # NaN
    if pd.isna(value):
        return None

    # numpy型
    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        if pd.isna(value):
            return None
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    # datetime
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()

    # dictなら中身も再帰的に変換
    if isinstance(value, dict):
        return {
            k: clean_value(v)
            for k, v in value.items()
        }

    # listなら中身も再帰的に変換
    if isinstance(value, list):
        return [
            clean_value(v)
            for v in value
        ]

    return value


def convert_json(value):

    value = clean_value(value)

    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, str):

        text = value.strip()

        if text == "":
            return None

        try:
            return clean_value(json.loads(text))
        except Exception:
            return value

    return value


def clean_record(record, table):

    json_cols = JSON_COLUMNS.get(table, [])

    cleaned = {}

    for key, value in record.items():

        if key in json_cols:
            cleaned[key] = convert_json(value)
        else:
            cleaned[key] = clean_value(value)

    return cleaned


def migrate_table(conn, table):

    print(f"\n===== {table} =====")

    df = pd.read_sql_query(
        f"SELECT * FROM {table}",
        conn
    )

    if df.empty:
        print("データなし")
        return

    if table == "initial_data":
        print(repr(df.loc[0, "seg_data_json"]))
        print(type(df.loc[0, "seg_data_json"]))

    records = []

    for record in df.to_dict(orient="records"):

        # SQLiteに残っている不要列を削除
        record.pop("COLMUN", None)
        records.append(
            clean_record(record, table)
        )

    try:

        (
            supabase
            .table(table)
            .upsert(
                records,
                on_conflict=CONFLICT_KEYS[table]
            )
            .execute()
        )

        print(f"✅ {len(records)}件移行しました")

    except Exception as e:

        print("❌ エラー発生")
        print(e)

        # 問題のレコードを探す
        for i, record in enumerate(records):

            try:
                (
                    supabase
                    .table(table)
                    .upsert(
                        record,
                        on_conflict=CONFLICT_KEYS[table]
                    )
                    .execute()
                )

            except Exception as ex:
                print(f"\n問題レコード番号: {i}")
                print(record)
                raise ex


def main():

    conn = sqlite3.connect(SQLITE_DB)

    migrate_table(conn, "companies")
    migrate_table(conn, "initial_data")
    migrate_table(conn, "app_settings")

    conn.close()

    print("\n🎉 移行完了")


if __name__ == "__main__":
    main()