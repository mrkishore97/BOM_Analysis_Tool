import pandas as pd


COMPONENT_COST_COLUMNS = [
    "labor_costs",
    "burden_costs",
    "material_costs",
    "outside_costs",
]

COST_COLUMNS = [
    *COMPONENT_COST_COLUMNS,
    "total_costs",
]

ROLLED_COST_COLUMN_MAP = {
    "labor_costs": "rolled_labor_costs",
    "burden_costs": "rolled_burden_costs",
    "material_costs": "rolled_material_costs",
    "outside_costs": "rolled_outside_costs",
    "total_costs": "rolled_total_costs",
}


def _parse_hierarchy_index(index_value):
    """Parse a dotted hierarchy index into a tuple of integers, or None if invalid."""
    if pd.isna(index_value):
        return None

    index_text = str(index_value).strip()
    if not index_text:
        return None

    segments = index_text.split(".")
    if any(not segment.isdigit() for segment in segments):
        return None

    return tuple(int(segment) for segment in segments)


def _coerce_cost_series(series: pd.Series) -> pd.Series:
    """Convert a cost series to numeric values without raising on imperfect exports."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    cleaned = (
        series.astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _clamp_direct_cost(value):
    """Return zero for tiny residual or negative direct costs that should not display."""
    if pd.isna(value):
        return value

    return 0 if abs(value) < 0.005 or value < 0 else value


def convert_rolled_costs_to_direct_costs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preserve ERP rolled-up cost columns and replace display cost columns with direct costs.

    Direct costs are calculated as the current row's rolled-up cost minus the rolled-up
    costs of its immediate children in the dotted hierarchy index. Rows with malformed
    or missing indexes are left unchanged so imperfect ERP exports do not fail uploads.
    """
    if "index" not in df.columns:
        return df

    present_cost_columns = [column for column in COST_COLUMNS if column in df.columns]
    present_component_columns = [
        column for column in COMPONENT_COST_COLUMNS if column in df.columns
    ]

    for cost_column in present_cost_columns:
        rolled_column = ROLLED_COST_COLUMN_MAP[cost_column]
        if rolled_column not in df.columns:
            df[rolled_column] = df[cost_column]

    parsed_indexes = df["index"].apply(_parse_hierarchy_index)
    immediate_children_by_parent = {}
    for row_position, hierarchy_key in enumerate(parsed_indexes):
        if hierarchy_key is None or len(hierarchy_key) <= 1:
            continue
        parent_key = hierarchy_key[:-1]
        immediate_children_by_parent.setdefault(parent_key, []).append(row_position)

    for cost_column in present_component_columns:
        rolled_column = ROLLED_COST_COLUMN_MAP[cost_column]
        rolled_values = _coerce_cost_series(df[rolled_column])
        direct_values = df[cost_column].copy()

        for row_position, hierarchy_key in enumerate(parsed_indexes):
            if hierarchy_key is None:
                continue

            current_rolled_value = rolled_values.iloc[row_position]
            if pd.isna(current_rolled_value):
                continue

            child_positions = immediate_children_by_parent.get(hierarchy_key, [])
            child_rolled_sum = (
                rolled_values.iloc[child_positions].dropna().sum()
                if child_positions
                else 0
            )
            direct_values.iloc[row_position] = _clamp_direct_cost(
                current_rolled_value - child_rolled_sum
            )

        df[cost_column] = direct_values

    if "total_costs" in df.columns and all(
        column in df.columns for column in COMPONENT_COST_COLUMNS
    ):
        direct_component_values = pd.concat(
            [_coerce_cost_series(df[column]) for column in COMPONENT_COST_COLUMNS],
            axis=1,
        )
        df["total_costs"] = direct_component_values.sum(axis=1).apply(
            _clamp_direct_cost
        )

    return df


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
    df_excel = convert_rolled_costs_to_direct_costs(df_excel)
    return df_excel

# Your actual cost calculation function
def get_costs(df: pd.DataFrame, labor_rate, labor_hours):
    total_cost = df.iloc[0]['total_costs']
    outside_cost = df.iloc[0]['outside_costs']
    material_cost = df.iloc[0]['material_costs']
    labor_cost = labor_rate * labor_hours
    final_cost = labor_cost + total_cost
    return total_cost, outside_cost, material_cost, labor_cost, final_cost
