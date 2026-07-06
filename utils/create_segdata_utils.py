
import pandas as pd

def create_segment_dataframe(seg_by_quarter):

    if not seg_by_quarter:
        return None, None
   
    q_order = {"1Q": 1, "2Q": 2, "3Q": 3, "4Q": 4}
    valid_seg_keys = [k for k in seg_by_quarter.keys() if "_" in k and k.split("_")[0].isdigit() and k.split("_")[1] in q_order]
     
    if not valid_seg_keys:
        return None, None
    
    sorted_seg_keys = sorted(valid_seg_keys, key=lambda k: (int(k.split("_")[0]), q_order.get(k.split("_")[1], 0)))

    all_segment_names = set(s.get("name") for seg_list in seg_by_quarter.values() for s in seg_list if s.get("name"))       
    ordered_labels = []
    seg_records = []

    for lk in sorted_seg_keys:
        year_str, q_str = lk.split("_")
        label = f"{year_str}\n{q_str}"
        if label not in ordered_labels:
            ordered_labels.append(label)
               
        for s in seg_by_quarter[lk]:
            seg_records.append({
                "PeriodLabel": label,
                "Year": int(year_str),
                "Quarter": q_str,
                "Name": s.get("name"),
                "Revenue_Cum": s.get("revenue_million"),
                "Profit_Cum": s.get("profit_million")
            })
               
    df_seg_cum = pd.DataFrame(seg_records)
    
    if df_seg_cum.empty:
        return None, None

    seg_standalone_records = []

    for name in all_segment_names:
        df_sub = df_seg_cum[df_seg_cum["Name"] == name]

        for year, df_year_sub in df_sub.groupby("Year"):
            df_year = df_year_sub.set_index("Quarter")
            for i, q in enumerate(["1Q", "2Q", "3Q", "4Q"]):
                if q in df_year.index:
                    current_row = df_year.loc[q]
                    rev_cum, prof_cum = current_row["Revenue_Cum"], current_row["Profit_Cum"]
                    p_label = current_row["PeriodLabel"]
                       
                    if i == 0:
                        rev_std, prof_std = rev_cum, prof_cum
                    else:
                        prev_q = ["1Q", "2Q", "3Q", "4Q"][i-1]
                        rev_std = rev_cum - df_year.loc[prev_q]["Revenue_Cum"] if rev_cum is not None and prev_q in df_year.index and df_year.loc[prev_q]["Revenue_Cum"] is not None else None
                        prof_std = prof_cum - df_year.loc[prev_q]["Profit_Cum"] if prof_cum is not None and prev_q in df_year.index and df_year.loc[prev_q]["Profit_Cum"] is not None else None
                             
                    seg_standalone_records.append({
                        "PeriodLabel": p_label, "Segment": name, "Revenue": rev_std, "Profit": prof_std,
                        "SortOrder": year * 10 + i
                    })
                           
    df_seg_std = pd.DataFrame(seg_standalone_records)
      
    if df_seg_std.empty:
        return None, None
    df_seg_std = df_seg_std.sort_values("SortOrder")
          
    df_pivot_rev = df_seg_std.pivot(index="PeriodLabel", columns="Segment", values="Revenue").reindex(ordered_labels)
    df_pivot_prof = df_seg_std.pivot(index="PeriodLabel", columns="Segment", values="Profit").reindex(ordered_labels)
          
    df_pivot_rev = df_pivot_rev.apply(pd.to_numeric, errors='coerce').fillna(0)
    df_pivot_prof = df_pivot_prof.apply(pd.to_numeric, errors='coerce').fillna(0)

    return df_pivot_rev, df_pivot_prof


