import pandas as pd

# Your actual BOM processing function
def process_bom_excel(file) -> pd.DataFrame:
    # Step 1: Read Excel
    df_excel = pd.read_excel(file)
    # Step 2: Create new column for moved descriptions
    df_excel['Description_Moved'] = None
    for i in range(1, len(df_excel), 2):
        if i < len(df_excel):
            df_excel.loc[i-1, 'Description_Moved'] = df_excel.loc[i, 'Level']
    # Step 3: Drop moved rows and reset index
    df_excel = df_excel.drop(range(1, len(df_excel), 2)).reset_index(drop=True)
    # Step 4: Clean up text
    df_excel['Description_Moved'] = (
        df_excel['Description_Moved'].astype(str).str.replace('_x000d__x000a_', ' ')
    )
    df_excel['Level'] = df_excel['Level'].astype(str).str.replace('*', '', regex=False)
    # Step 5: Rename columns
    df_excel.columns = [
        'level', 'part_number', 'rev', 'unit', 'needed',
        'labor_costs', 'burden_costs', 'material_costs',
        'outside_costs', 'misc_costs', 'total_costs', 'description'
    ]
    # Step 6: Reorder columns
    cols = df_excel.columns.tolist()
    cols.remove('description')
    cols.insert(2, 'description')
    df_excel = df_excel.reindex(columns=cols)
    # Step 7: Add code column
    def get_code(part: str) -> str:
        if part.startswith("2B"):
            return "RAW"
        for prefix in ["2B", "2M","3M", "4M", "5M"]:
            if prefix in part:
                return prefix
        return "6"
    df_excel["code"] = df_excel["part_number"].astype(str).apply(get_code)
    # Step 8: Drop unwanted columns
    df_excel = df_excel.drop(columns=['rev', 'misc_costs'])
    # Step 9: Drop the last row
    df_excel.drop(df_excel.tail(1).index, inplace=True)
    # Step 10: Generate index column
    def generate_index(levels):
        counters = {}
        result = []
        for lvl in levels:
            # Reset deeper levels if we move up
            counters = {k: v for k, v in counters.items() if k <= lvl}
            counters[lvl] = counters.get(lvl, 0) + 1
            # Build string like "1.1.2"
            idx = ".".join(str(counters[i]) for i in sorted(counters))
            result.append(idx)
        return result
    df_excel["index"] = generate_index(df_excel["level"].astype(int).tolist())
    return df_excel

# Your actual cost calculation function
def get_costs(df: pd.DataFrame, labor_rate, labor_hours):
    total_cost = df.iloc[0]['total_costs']
    outside_cost = df.iloc[0]['outside_costs']
    material_cost = df.iloc[0]['material_costs']
    labor_cost = labor_rate * labor_hours
    final_cost = labor_cost + total_cost
    return total_cost, outside_cost, material_cost, labor_cost, final_cost

