import pandas as pd

# ---------------------------------------------------------
# 
# ---------------------------------------------------------

# --- 📈 数据処理・描画のヘルパー関数 ---
def process_to_8quarters(combined_data):
    records = []
    if not combined_data:
        return pd.DataFrame()
   
    q_order = {"1Q": 1, "2Q": 2, "3Q": 3, "4Q": 4}

    def get_sort_key(key_str):
        parts = key_str.split("_")
        return (int(parts[0]), q_order.get(parts[1], 0))
   
    sorted_keys = sorted(combined_data.keys(), key=get_sort_key)

    for key in sorted_keys:
        year_str, q_str = key.split("_")
        year = int(year_str)
        current_q_data = combined_data[key]
   
        if not current_q_data or current_q_data.get("revenue") is None:
            continue
       
        rev = None
        inc = None
   
        if q_str == "1Q":
            rev = current_q_data["revenue"]
            inc = current_q_data["operating_income"]
        else:
            q_list = ["1Q", "2Q", "3Q", "4Q"]
            current_idx = q_list.index(q_str)
            prev_q_str = q_list[current_idx - 1]
            prev_key = f"{year}_{prev_q_str}"
       
            if prev_key in combined_data and combined_data[prev_key] and combined_data[prev_key].get("revenue") is not None:
                rev = current_q_data["revenue"] - combined_data[prev_key]["revenue"]
                inc = current_q_data["operating_income"] - combined_data[prev_key]["operating_income"]
   
        records.append({
            "QuarterKey": key,
            "Period": f"{year_str}/\n{q_str}",
            "Year": year,
            "Quarter": q_str,
            "Revenue": rev,
            "Income": inc
        })
   
    return pd.DataFrame(records)
