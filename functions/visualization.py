
import pandas as pd
import plotly.express as px
import streamlit as st
from functions.analysis import pareto_analysis

# Your actual visualization functions
def plot_first_row_pie_chart(df, labor_rate=0, labor_hours=0, include_labor=False):
    """
    Returns a Plotly pie chart figure for the first row of the DataFrame.
    """
    if df.empty:
        st.error("DataFrame is empty.")
        return None

    first_row = df.iloc[0]

    costs = {
        'Material Costs': first_row.get('material_costs', 0),
        'Outside Costs': first_row.get('outside_costs', 0)
    }

    if include_labor and labor_rate > 0 and labor_hours > 0:
        costs['Labor Costs'] = labor_rate * labor_hours

    # Remove zero costs
    costs = {k: v for k, v in costs.items() if v > 0}

    if costs:
        fig = px.pie(
            values=list(costs.values()),
            names=list(costs.keys()),
            title=f"Cost Breakdown for Part: {first_row['part_number']} ({first_row['description'][:50]}...)"
        )
        return fig
    else:
        st.warning("No cost data available for the first row.")
        return None


def plot_code_distribution_pie_chart(df, selected_codes=None):
    """
    Returns a Plotly pie chart figure for unique part numbers per code.
    """
    if df.empty:
        st.error("DataFrame is empty.")
        return None

    if 'code' not in df.columns or 'part_number' not in df.columns:
        st.error("DataFrame must have both 'code' and 'part_number' columns.")
        return None

    code_counts = df.groupby('code')['part_number'].nunique().reset_index()
    code_counts.columns = ['code', 'count']

    default_codes = ['2B', '3M', '2M', '4M', '5M', '6', 'RAW']
    codes_to_use = selected_codes if selected_codes else default_codes

    code_counts_filtered = code_counts[code_counts['code'].isin(codes_to_use)]

    if not code_counts_filtered.empty:
        fig = px.pie(
            code_counts_filtered,
            values='count',
            names='code',
            title=f'Unique Part Numbers per Code ({", ".join(codes_to_use)})'
        )
        return fig
    else:
        st.warning("No data available for the selected codes.")
        return None


def plot_aggregate_costs_pie_chart(df, selected_codes=None):
    """
    Returns a Plotly pie chart figure for aggregate costs per code.
    """
    if df.empty:
        st.error("DataFrame is empty.")
        return None

    if 'code' not in df.columns or 'costs_1' not in df.columns:
        st.error("DataFrame must have both 'code' and 'costs_1' columns.")
        return None

    default_codes = ['2B', '3M', 'RAW']
    codes_to_use = selected_codes if selected_codes else default_codes

    code_costs = (
        df[df['code'].isin(codes_to_use)]
        .groupby('code')['costs_1']
        .sum()
        .reset_index()
    )
    code_costs.columns = ['code', 'total_costs']

    if not code_costs.empty:
        fig = px.pie(
            code_costs,
            values='total_costs',
            names='code',
            title=f'Distribution of Aggregate Costs ({", ".join(codes_to_use)})'
        )
        return fig
    else:
        st.warning("No cost data available for the selected codes.")
        return None


def cost_quantity_bubble_chart_interactive(df, scale="linear", code_filter=None, bubble_scale=0.1):
    """
    Interactive Bubble chart: Needed Quantity vs. Cost
    scale options: "linear", "log", "sqrt", "focus_cluster"
    Designed for Streamlit embedding.
    """
    # --- Get filtered Pareto data ---
    pareto_df, total_sum = pareto_analysis(
        df,
        code_filter=["3M","2B","RAW"] if code_filter is None else code_filter,
        top_n=None,
        aggregate=True
    )
    data = pareto_df.copy()

    # --- Scaling transforms ---
    if scale == "sqrt":
        data["x_val"] = np.sqrt(data["needed"])
        data["y_val"] = np.sqrt(data["costs_1"])
        x_label = "√ Needed Quantity"
        y_label = "√ Total Cost"
    else:
        data["x_val"] = data["needed"]
        data["y_val"] = data["costs_1"]
        x_label = "Needed Quantity"
        y_label = "Total Cost"

    # --- Interactive bubble chart ---
    fig = px.scatter(
        data,
        x="x_val",
        y="y_val",
        size=data["costs_1"] * bubble_scale,  # bubble size
        color="code" if "code" in data.columns else None,  # optional color by code
        hover_name="part_number",
        hover_data={"needed": True, "costs_1": True, "x_val": False, "y_val": False},
        opacity=0.7,
    )

    # --- Axis scaling modes ---
    if scale == "log":
        fig.update_xaxes(type="log")
        fig.update_yaxes(type="log")
    elif scale == "focus_cluster":
        x_max = data["needed"].quantile(0.95)
        y_max = data["costs_1"].quantile(0.95)
        fig.update_xaxes(range=[0, x_max * 1.1])
        fig.update_yaxes(range=[0, y_max * 1.1])
    elif scale == "linear":
        fig.update_xaxes(range=[0, data["needed"].max() * 1.1])
        fig.update_yaxes(range=[0, data["costs_1"].max() * 1.1])

    # --- Labels and layout ---
    fig.update_layout(
        title="High-Cost/Low-Qty vs. Low-Cost/High-Qty Parts",
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
        showlegend=True,
    )

    return fig

