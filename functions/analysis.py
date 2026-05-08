import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np

def pareto_analysis(df, level_filter=None, code_filter=None, top_n=None, aggregate=True):
    """
    Pareto analysis function with filtering and aggregation options.
    """
    data = df.copy()
    total_sum = data.loc[0, 'total_costs']
    data['costs_1'] = np.where(data['outside_costs'] != 0, data['outside_costs'], data['total_costs'])

    # --- Apply level filter ---
    if level_filter:
        if not isinstance(level_filter, (list, tuple, set)):
            level_filter = [level_filter]
        data = data[data['level'].isin(level_filter)]

    # --- Apply code filter ---
    if code_filter:
        if not isinstance(code_filter, (list, tuple, set)):
            code_filter = [code_filter]
        data = data[data['code'].isin(code_filter)]

    # --- Aggregate by part_number ---
    if aggregate:
        grouped = (
            data.groupby("part_number", as_index=False).agg({
                "description": "first",
                "unit": "first",
                "code": "first",
                "needed": "sum",
                "labor_costs": "sum",
                "burden_costs": "sum",
                "material_costs": "sum",
                "outside_costs": "sum",
                "total_costs": "sum",
                "costs_1": "sum"
            })
        )
    else:
        grouped = data[[
            "part_number", "description", "needed", "costs_1", "code",
            "material_costs", "outside_costs", "total_costs"
        ]].copy()

    # --- Sort descending ---
    grouped = grouped.sort_values("costs_1", ascending=False).reset_index(drop=True)

    # --- Individual % contribution ---
    grouped["row_perc"] = 100 * grouped["costs_1"] / total_sum

    # --- Cumulative % ---
    grouped["cum_cost"] = grouped["costs_1"].cumsum()
    grouped["cum_perc"] = 100 * grouped["cum_cost"] / total_sum

    if top_n:
        grouped = grouped.head(top_n)

    return grouped, total_sum

def plot_pareto_analysis(pareto_df):
    """
    Returns an interactive Pareto analysis chart as a Plotly figure.
    - Bars: individual % contribution of each part number
    - Line: cumulative % contribution
    """
    if pareto_df.empty:
        st.error("Pareto DataFrame is empty.")
        return None

    fig = go.Figure()

    # --- Bar chart: individual % ---
    fig.add_trace(go.Bar(
        x=pareto_df["part_number"],
        y=pareto_df["row_perc"],
        name="Individual %",
        marker_color="skyblue"
    ))

    # --- Line chart: cumulative % ---
    fig.add_trace(go.Scatter(
        x=pareto_df["part_number"],
        y=pareto_df["cum_perc"],
        mode="lines+markers",
        name="Cumulative %",
        line=dict(color="red", width=2),
        marker=dict(size=6),
        yaxis="y2"
    ))

    # --- Add 80% threshold line ---
    fig.add_hline(
        y=80,
        line=dict(color="green", dash="dash"),
        annotation_text="80% Threshold",
        annotation_position="top left"
    )

    # --- Layout ---
    fig.update_layout(
        title="Pareto Analysis",
        xaxis_title="Part Number",
        yaxis_title="Individual % of Total Cost",
        yaxis=dict(side="left", range=[0, 100]),
        yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 100]),
        legend=dict(x=0.8, y=1.1, orientation="h"),
        margin=dict(l=40, r=40, t=80, b=120),
        bargap=0.2,
        height=500
    )

    return fig


def calculate_and_visualize_profit_loss(df, labor_rate=0, labor_hours=0, selling_cost=0, calculate_margin=False):
    """
    Calculates profit/loss and visualizes results: bar chart, pie chart, and line chart side by side.
    Returns all cost values for further use.
    """
    if df.empty:
        st.error("DataFrame is empty.")
        return None

    if not calculate_margin:
        return None

    if labor_rate <= 0 or labor_hours <= 0 or selling_cost <= 0:
        st.warning("Please provide valid Labor Rate, Labor Hours, and Selling Price.")
        return None

    # --- First row costs ---
    first_row = df.iloc[0]
    material_costs = first_row.get('material_costs', 0)
    outside_costs = first_row.get('outside_costs', 0)
    labor_costs = labor_rate * labor_hours
    total_cost = labor_costs + material_costs + outside_costs

    # --- Profit / Loss ---
    profit_loss_value = selling_cost - total_cost
    profit_loss_percentage = (profit_loss_value / selling_cost) * 100

    # --- Prepare visualizations ---
    # 1️⃣ Bar chart
    bar_data = {
        "Category": ["Total Cost", "Selling Price"],
        "Value": [total_cost, selling_cost]
    }
    fig_bar = px.bar(
        bar_data,
        x="Category",
        y="Value",
        color="Category",
        text="Value",
        title="Cost vs Selling Price"
    )
    fig_bar.update_traces(texttemplate="$%{text:,.2f}", textposition="outside")

    # 2️⃣ Pie chart
    breakdown = {
        "Labor Costs": labor_costs,
        "Material Costs": material_costs,
        "Outside Costs": outside_costs
    }
    if profit_loss_value >= 0:
        breakdown["Profit"] = profit_loss_value
        colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
    else:
        breakdown["Loss"] = -profit_loss_value
        colors = ["#636EFA", "#EF553B", "#00CC96", "#FF4136"]

    fig_pie = px.pie(
        names=list(breakdown.keys()),
        values=list(breakdown.values()),
        title="Cost & Profit/Loss Breakdown",
        color=list(breakdown.keys()),
        color_discrete_sequence=colors
    )
    fig_pie.update_traces(texttemplate="%{label}: $%{value:,.2f}", textposition="inside")

    # 3️⃣ Line chart: Profit Margin vs Total Costs
    total_costs_range = [total_cost * 0.9, total_cost * 0.95, total_cost, total_cost * 1.05, total_cost * 1.1]
    profit_margin_range = [(selling_cost - x)/selling_cost*100 for x in total_costs_range]

    fig_line = go.Figure(data=go.Scatter(
        x=total_costs_range,
        y=profit_margin_range,
        mode='lines+markers',
        name='Profit Margin',
        line=dict(color='blue', width=2)
    ))
    fig_line.update_layout(
        title='Profit Margin vs Total Costs',
        xaxis_title='Total Costs ($)',
        yaxis_title='Profit Margin (%)',
        template="plotly_white"
    )

    # --- Return figures and cost data ---
    return {
        "fig_bar": fig_bar,
        "fig_pie": fig_pie,
        "fig_line": fig_line,
        "labor_costs": labor_costs,
        "material_costs": material_costs,
        "outside_costs": outside_costs,
        "total_cost": total_cost,
        "profit_loss_value": profit_loss_value,
        "profit_loss_percentage": profit_loss_percentage
    }

def analyze_filtered_pareto(df):
    """
    Calls pareto_analysis, then filters and sorts the result by code and cost.
    """
    # Call pareto_analysis
    pareto_df, total_sum = pareto_analysis(df, code_filter=None, top_n=None, aggregate=True)

    # Filter by 3M and sort by outside_costs
    filtered_3m = pareto_df[pareto_df['code'] == '3M'].sort_values('outside_costs', ascending=False)

    # Filter by 2B and sort by material_costs
    filtered_2b = pareto_df[pareto_df['code'] == '2B'].sort_values('material_costs', ascending=False)

    # Filter by RAW and sort by material_costs
    filtered_raw = pareto_df[pareto_df['code'] == 'RAW'].sort_values('material_costs', ascending=False)

    return filtered_3m, filtered_2b, filtered_raw