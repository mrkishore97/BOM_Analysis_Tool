import streamlit as st
import pandas as pd
from io import BytesIO
from functions.data_processing import process_bom_excel, get_costs
from functions.visualization import plot_first_row_pie_chart, plot_code_distribution_pie_chart, plot_aggregate_costs_pie_chart, cost_quantity_bubble_chart_interactive
from functions.analysis import pareto_analysis, calculate_and_visualize_profit_loss, plot_pareto_analysis, analyze_filtered_pareto
from functions.bom_structure import visualize_bom_streamlit


def format_quantity_value(value):
    """Format whole-number quantities without decimals and fractional quantities to two decimals."""
    if pd.isna(value):
        return ""

    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


# Configure page
st.set_page_config(page_title="BOM Analysis Tool", layout="wide")

# Initialize session state
if 'df_excel' not in st.session_state:
    st.session_state.df_excel = None
# ... (all other session state initializations)

# Sidebar navigation
st.sidebar.title("Navigation")

# =============================================================================
# INITIALIZE SESSION STATE
# This section runs once when the app first loads
# It creates "storage slots" that persist across button clicks
# =============================================================================
if 'df_excel' not in st.session_state:
    st.session_state.df_excel = None  # Stores processed BOM data

if 'kpis' not in st.session_state:
    st.session_state.kpis = None  # Stores calculated KPIs

if 'complete_df' not in st.session_state:
    st.session_state.complete_df = None  # Stores pareto analysis dataframe

if 'complete_sum' not in st.session_state:
    st.session_state.complete_sum = None  # Stores pareto analysis sum

if 'visualization' not in st.session_state:
    st.session_state.visualization = None  # Stores visualization HTML content

if 'viz_file_path' not in st.session_state:
    st.session_state.viz_file_path = None  # Stores temp file path for download

if 'pareto_data' not in st.session_state:
    st.session_state.pareto_data = None  # Stores Pareto analysis data

if 'include_labor_chart' not in st.session_state:
    st.session_state.include_labor_chart = False  # Checkbox state for labor in chart

if 'profit_loss_data' not in st.session_state:
    st.session_state.profit_loss_data = None  # Stores profit/loss visualization data

if 'analysis_mode' not in st.session_state:
    st.session_state.analysis_mode = 'default'  # 'default' or 'custom'

if 'filtered_pareto_data' not in st.session_state:
    st.session_state.filtered_pareto_data = None  # Stores filtered pareto data (3M, 2B, RAW)

if 'bubble_scale_option' not in st.session_state:
    st.session_state.bubble_scale_option = 'linear'  # Default scale for bubble chart

if 'bubble_size' not in st.session_state:
    st.session_state.bubble_size = 0.1  # Default bubble size multiplier

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["BOM Analysis Tool", "BOM Visualization", "Pareto Analysis"])

# =============================================================================
# PAGE 1: BOM ANALYSIS TOOL
# =============================================================================
if page == "BOM Analysis Tool":
    st.title("BOM ANALYSIS TOOL")

    # Sidebar inputs
    with st.sidebar:
        st.header("Input Parameters")

        uploaded_file = st.file_uploader("Upload Excel Sheet", type=['xlsx', 'xls'])

        labor_rate = st.number_input("Labor Rate", min_value=0.0, value=0.0, step=1.0)
        labor_hour = st.number_input("Labor Hour", min_value=0.0, value=0.0, step=1.0)

        st.markdown("---")

        # Selling cost and margin calculation inputs
        selling_cost = st.number_input("Selling Cost", min_value=0.0, value=0.0, step=100.0)
        calculate_margin = st.checkbox("Calculate Margin", value=False)

        st.markdown("---")
        process_btn = st.button("Process", type="primary", use_container_width=True)
        download_btn = st.button("Download", use_container_width=True)

    # Main content
    st.header("KPIS")

    # Process data when button clicked
    if process_btn:
        if uploaded_file is not None:
            with st.spinner("Processing BOM data..."):
                # Process the uploaded file using your function
                st.session_state.df_excel = process_bom_excel(uploaded_file)

                # Calculate KPIs using your function
                total_cost, outside_cost, material_cost, labor_cost, final_cost = get_costs(
                    st.session_state.df_excel,
                    labor_rate,
                    labor_hour
                )

                # Store KPIs in session state
                st.session_state.kpis = {
                    'total_cost': total_cost,
                    'outside_cost': outside_cost,
                    'material_cost': material_cost,
                    'labor_cost': labor_cost,
                    'final_cost': final_cost,
                    'labor_rate': labor_rate,
                    'labor_hour': labor_hour
                }

                # Calculate pareto analysis data for the third chart
                st.session_state.complete_df, st.session_state.complete_sum = pareto_analysis(
                    st.session_state.df_excel,
                    level_filter=None,
                    code_filter=['3M', '2B', 'RAW'],
                    top_n=None,
                    aggregate=True
                )

                # Calculate profit/loss visualization if margin calculation is enabled
                st.session_state.profit_loss_data = calculate_and_visualize_profit_loss(
                    st.session_state.df_excel,
                    labor_rate=labor_rate,
                    labor_hours=labor_hour,
                    selling_cost=selling_cost,
                    calculate_margin=calculate_margin
                )

            st.success("✅ Processing complete!")
        else:
            st.error("⚠️ Please upload an Excel file first!")

    # Display KPIs or message
    if st.session_state.kpis:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Costs", f"${st.session_state.kpis['total_cost']:,.2f}")

        with col2:
            st.metric("Total Outside Costs", f"${st.session_state.kpis['outside_cost']:,.2f}")

        with col3:
            st.metric("Total Material Costs", f"${st.session_state.kpis['material_cost']:,.2f}")

        # Second row of KPIs
        col4, col5 = st.columns(2)

        with col4:
            # Check if labor values were entered
            if st.session_state.kpis['labor_rate'] > 0 and st.session_state.kpis['labor_hour'] > 0:
                st.metric("Labor Costs", f"${st.session_state.kpis['labor_cost']:,.2f}")
            else:
                st.metric("Labor Costs", "Not Entered", help="Please enter Labor Rate and Labor Hour values")

        with col5:
            # Check if labor values were entered for final cost
            if st.session_state.kpis['labor_rate'] > 0 and st.session_state.kpis['labor_hour'] > 0:
                st.metric("Final Costs Including Labor", f"${st.session_state.kpis['final_cost']:,.2f}")
            else:
                st.metric("Final Costs (Without Labor)", f"${st.session_state.kpis['total_cost']:,.2f}",
                          help="Enter Labor Rate and Labor Hour to include labor costs")
    else:
        st.info("📊 Upload data and click Process to view KPIs")

    # Display figures - Now with actual pie charts
    st.markdown("---")

    if st.session_state.df_excel is not None and st.session_state.kpis is not None:
        # First row of charts
        col1, col2, col3 = st.columns(3)

        with col1:
            # Checkbox for including labor in first chart
            include_labor = st.checkbox("Include Labor Costs in Chart 1", value=st.session_state.include_labor_chart,
                                        key="labor_checkbox")
            st.session_state.include_labor_chart = include_labor

            fig1 = plot_first_row_pie_chart(
                st.session_state.df_excel,
                labor_rate=st.session_state.kpis['labor_rate'],
                labor_hours=st.session_state.kpis['labor_hour'],
                include_labor=include_labor
            )
            if fig1:
                st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = plot_code_distribution_pie_chart(st.session_state.df_excel)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True)

        with col3:
            # Use complete_df from pareto_analysis for the third chart
            if st.session_state.complete_df is not None:
                fig3 = plot_aggregate_costs_pie_chart(st.session_state.complete_df, selected_codes=['2B', '3M', 'RAW'])
                if fig3:
                    st.plotly_chart(fig3, use_container_width=True)

        # Second row of charts - Profit/Loss visualizations
        st.markdown("---")

        if st.session_state.profit_loss_data is not None:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.plotly_chart(st.session_state.profit_loss_data['fig_bar'], use_container_width=True)
            with col2:
                st.plotly_chart(st.session_state.profit_loss_data['fig_pie'], use_container_width=True)
            with col3:
                st.plotly_chart(st.session_state.profit_loss_data['fig_line'], use_container_width=True)

            # Display profit/loss summary
            st.markdown("### Profit/Loss Summary")
            summary_col1, summary_col2 = st.columns(2)
            with summary_col1:
                profit_loss_val = st.session_state.profit_loss_data['profit_loss_value']
                if profit_loss_val >= 0:
                    st.success(f"✅ **Profit:** ${profit_loss_val:,.2f}")
                else:
                    st.error(f"❌ **Loss:** ${abs(profit_loss_val):,.2f}")
            with summary_col2:
                st.metric("Profit/Loss Percentage",
                          f"{st.session_state.profit_loss_data['profit_loss_percentage']:.2f}%")
        else:
            st.info("💰 Enable 'Calculate Margin' checkbox and provide Selling Cost to view profit/loss analysis")
    else:
        st.info("📈 Upload data and click Process to view charts")

    # Scrollable dataframe
    st.markdown("---")
    st.subheader("BOM Data - Detailed View")
    if st.session_state.df_excel is not None:
        # Select only specific columns to display
        columns_to_display = ['part_number', 'index', 'needed', 'code', 'outside_costs', 'material_costs', 'total_costs']

        # Check if all columns exist in the dataframe
        available_columns = [col for col in columns_to_display if col in st.session_state.df_excel.columns]

        if available_columns:
            df_display = st.session_state.df_excel[available_columns].copy()

            # Format quantity and currency columns for better readability
            if 'needed' in df_display.columns:
                qty_values = pd.to_numeric(df_display['needed'], errors='coerce')
                df_display['needed'] = qty_values.apply(
                    format_quantity_value
                )

            currency_cols = ['outside_costs', 'material_costs', 'total_costs']
            for col in currency_cols:
                if col in df_display.columns:
                    df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")

            df_display = df_display.rename(columns={
                'needed': 'Qty',
                'outside_costs': 'Direct Outside Costs',
                'material_costs': 'Direct Material Costs',
                'total_costs': 'Direct Total Costs'
            })

            # Display the dataframe with scrolling
            st.dataframe(
                df_display,
                use_container_width=True,
                height=400,
                hide_index=True
            )

            # Show record count
            st.caption(f"Showing {len(df_display)} records")
        else:
            st.warning("Required columns not found in the dataframe")
    else:
        st.info("Upload and process data to view the dataframe")

    # Download functionality
    if download_btn:
        if st.session_state.df_excel is not None:
            # Create Excel file in memory
            from io import BytesIO

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.df_excel.to_excel(writer, index=False, sheet_name='BOM Data')

            excel_data = output.getvalue()

            st.download_button(
                label="📥 Download Processed Data (Excel)",
                data=excel_data,
                file_name="processed_bom_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.error("⚠️ No data to download. Please process data first!")

# =============================================================================
# PAGE 2: BOM VISUALIZATION
# =============================================================================
elif page == "BOM Visualization":
    st.title("BOM VISUALIZATION")

    # Top action buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        process_viz_btn = st.button("🔄 Process Visualization", type="primary", use_container_width=True)
    with col2:
        if st.session_state.viz_file_path:
            with open(st.session_state.viz_file_path, 'rb') as f:
                st.download_button(
                    label="📥 Download HTML",
                    data=f,
                    file_name="bom_visualization.html",
                    mime="text/html",
                    use_container_width=True
                )
        else:
            st.button("📥 Download HTML", disabled=True, use_container_width=True)
    with col3:
        if st.session_state.viz_file_path:
            # Create a link that opens the visualization in a new tab
            st.markdown(
                f'<a href="data:text/html;base64,{st.session_state.visualization.encode().hex()}" '
                f'target="_blank" style="display: inline-block; padding: 0.5rem 1rem; '
                f'background-color: #FF4B4B; color: white; text-decoration: none; '
                f'border-radius: 0.5rem; text-align: center; width: 100%;">🔗 Open in New Tab</a>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="display: inline-block; padding: 0.5rem 1rem; '
                'background-color: #cccccc; color: #666666; text-decoration: none; '
                'border-radius: 0.5rem; text-align: center; width: 100%;">🔗 Open in New Tab (Disabled)</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # Process visualization
    if process_viz_btn:
        if st.session_state.df_excel is not None:
            with st.spinner("Generating BOM visualization..."):
                try:
                    html_content, file_path = visualize_bom_streamlit(st.session_state.df_excel)
                    st.session_state.visualization = html_content
                    st.session_state.viz_file_path = file_path
                    st.success("✅ Visualization generated successfully!")
                except Exception as e:
                    st.error(f"❌ Error generating visualization: {str(e)}")
        else:
            st.warning("⚠️ Please upload and process data in the BOM Analysis Tool page first!")

    # Display visualization
    if st.session_state.visualization is not None:
        st.components.v1.html(st.session_state.visualization, height=850, scrolling=True)
    else:
        # Placeholder
        viz_placeholder = st.container(height=600)
        with viz_placeholder:
            st.markdown(
                "<div style='text-align: center; padding-top: 250px; font-size: 18px; color: #666;'>"
                "🎨 BOM Visualization with PYVIS<br><br>"
                "Click 'Process Visualization' to generate the interactive network diagram</div>",
                unsafe_allow_html=True
            )

# =============================================================================
# PAGE 3: PARETO ANALYSIS
# =============================================================================
elif page == "Pareto Analysis":
    st.title("PARETO ANALYSIS")

    # Analysis mode selection
    col1, col2 = st.columns(2)
    with col1:
        default_btn = st.button("Recommended Analysis (3M, 2B, RAW)", type="primary", use_container_width=True)
    with col2:
        custom_btn = st.button("Custom Analysis", use_container_width=True)

    # Set analysis mode
    if default_btn:
        st.session_state.analysis_mode = 'default'
    elif custom_btn:
        st.session_state.analysis_mode = 'custom'

    st.markdown("---")

    # Custom analysis controls
    if st.session_state.analysis_mode == 'custom':
        st.subheader("Custom Analysis Parameters")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**Code Filter**")
            available_codes = ['2B', '2M', '3M', '4M', '5M', '6', 'RAW']
            code_filter = st.multiselect(
                "Select codes to analyze",
                options=available_codes,
                default=['3M', '2B', 'RAW'],
                key="code_filter"
            )

        with col2:
            st.write("**Level Filter** (Optional)")
            if st.session_state.df_excel is not None:
                unique_levels = sorted(st.session_state.df_excel['level'].unique().tolist())
                level_filter = st.multiselect(
                    "Select levels (leave empty for all)",
                    options=unique_levels,
                    key="level_filter"
                )
            else:
                level_filter = []
                st.info("Process data first to see levels")

        with col3:
            st.write("**Top N Parts** (Optional)")
            top_n = st.number_input(
                "Limit to top N parts",
                min_value=0,
                value=0,
                step=1,
                help="0 means show all parts",
                key="top_n"
            )
            top_n = None if top_n == 0 else top_n

            aggregate = st.checkbox("Aggregate by Part Number", value=True, key="aggregate")

        process_btn = st.button("Run Custom Analysis", type="secondary", use_container_width=True)
    else:
        # Default mode - use recommended settings
        code_filter = ['3M', '2B', 'RAW']
        level_filter = None
        top_n = None
        aggregate = True
        process_btn = st.button("Run Recommended Analysis", type="secondary", use_container_width=True)

    st.markdown("---")

    # Run analysis
    if process_btn:
        if st.session_state.df_excel is not None:
            with st.spinner("Running Pareto analysis..."):
                try:
                    # Convert empty level_filter list to None
                    level_param = level_filter if level_filter else None

                    pareto_df, total_sum = pareto_analysis(
                        st.session_state.df_excel,
                        level_filter=level_param,
                        code_filter=code_filter,
                        top_n=top_n,
                        aggregate=aggregate
                    )

                    st.session_state.pareto_data = pareto_df

                    # Also run filtered pareto analysis for top_n parts tab
                    filtered_3m, filtered_2b, filtered_raw = analyze_filtered_pareto(st.session_state.df_excel)
                    st.session_state.filtered_pareto_data = {
                        '3M': filtered_3m,
                        '2B': filtered_2b,
                        'RAW': filtered_raw
                    }

                    st.success(
                        f"Analysis complete! Analyzing {len(pareto_df)} parts with total cost: ${total_sum:,.2f}")
                except Exception as e:
                    st.error(f"Error running analysis: {str(e)}")
        else:
            st.warning("Please upload and process data in the BOM Analysis Tool page first!")

    # Display results in tabs
    if st.session_state.pareto_data is not None:
        tab1, tab2, tab3, tab4 = st.tabs(["Data Frame", "Chart", "Top N Parts", "Bubble Chart"])

        with tab1:
            st.subheader("Pareto Data Frame")

            # Select only specific columns
            columns_to_display = ['part_number', 'description', 'needed', 'material_costs', 'outside_costs',
                                  'total_costs', 'row_perc', 'cum_perc']
            available_cols = [col for col in columns_to_display if col in st.session_state.pareto_data.columns]

            if available_cols:
                display_df = st.session_state.pareto_data[available_cols].copy()

                # Format quantity and currency columns for display
                if 'needed' in display_df.columns:
                    qty_values = pd.to_numeric(display_df['needed'], errors='coerce')
                    display_df['needed'] = qty_values.apply(
                        format_quantity_value
                    )

                currency_cols = ['material_costs', 'outside_costs', 'total_costs']
                for col in currency_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")

                # Format percentage columns
                percent_cols = ['row_perc', 'cum_perc']
                for col in percent_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

                display_df = display_df.rename(columns={'needed': 'Qty'})

                st.dataframe(display_df, use_container_width=True, height=500)

                # Download button for pareto data
                csv = (
                    st.session_state.pareto_data[available_cols]
                    .rename(columns={'needed': 'Qty'})
                    .to_csv(index=False)
                )
                st.download_button(
                    label="Download Pareto Analysis (CSV)",
                    data=csv,
                    file_name="pareto_analysis.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Required columns not found in pareto data")

        with tab2:
            st.subheader("Pareto Chart")
            fig = plot_pareto_analysis(st.session_state.pareto_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

                # Show 80% analysis
                parts_80 = st.session_state.pareto_data[st.session_state.pareto_data['cum_perc'] <= 80]
                if not parts_80.empty:
                    st.info(
                        f"**80/20 Rule:** {len(parts_80)} parts ({len(parts_80) / len(st.session_state.pareto_data) * 100:.1f}%) account for 80% of total costs")

        with tab3:
            st.subheader("Top N Parts by Code")

            if st.session_state.filtered_pareto_data is not None:
                # Columns to display for filtered data
                filtered_columns = ['part_number', 'description', 'needed', 'material_costs', 'outside_costs',
                                    'total_costs', 'row_perc']

                # 3M Parts
                st.markdown("### 3M - Outside Service (Sorted by Outside Costs)")
                if not st.session_state.filtered_pareto_data['3M'].empty:
                    df_3m = st.session_state.filtered_pareto_data['3M'].copy()
                    available_3m_cols = [col for col in filtered_columns if col in df_3m.columns]

                    if available_3m_cols:
                        display_3m = df_3m[available_3m_cols].copy()

                        # Format quantity
                        if 'needed' in display_3m.columns:
                            qty_values = pd.to_numeric(display_3m['needed'], errors='coerce')
                            display_3m['needed'] = qty_values.apply(
                                format_quantity_value
                            )

                        # Format currency
                        for col in ['material_costs', 'outside_costs', 'total_costs']:
                            if col in display_3m.columns:
                                display_3m[col] = display_3m[col].apply(
                                    lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")

                        # Format percentage
                        if 'row_perc' in display_3m.columns:
                            display_3m['row_perc'] = display_3m['row_perc'].apply(
                                lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

                        display_3m = display_3m.rename(columns={'needed': 'Qty'})

                        st.dataframe(display_3m, use_container_width=True, height=300)
                        st.caption(f"Showing {len(display_3m)} parts")
                else:
                    st.info("No 3M parts found")

                st.markdown("---")

                # 2B Parts
                st.markdown("### 2B - Bought Out (Sorted by Material Costs)")
                if not st.session_state.filtered_pareto_data['2B'].empty:
                    df_2b = st.session_state.filtered_pareto_data['2B'].copy()
                    available_2b_cols = [col for col in filtered_columns if col in df_2b.columns]

                    if available_2b_cols:
                        display_2b = df_2b[available_2b_cols].copy()

                        # Format quantity
                        if 'needed' in display_2b.columns:
                            qty_values = pd.to_numeric(display_2b['needed'], errors='coerce')
                            display_2b['needed'] = qty_values.apply(
                                format_quantity_value
                            )

                        # Format currency
                        for col in ['material_costs', 'outside_costs', 'total_costs']:
                            if col in display_2b.columns:
                                display_2b[col] = display_2b[col].apply(
                                    lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")

                        # Format percentage
                        if 'row_perc' in display_2b.columns:
                            display_2b['row_perc'] = display_2b['row_perc'].apply(
                                lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

                        display_2b = display_2b.rename(columns={'needed': 'Qty'})

                        st.dataframe(display_2b, use_container_width=True, height=300)
                        st.caption(f"Showing {len(display_2b)} parts")
                else:
                    st.info("No 2B parts found")

                st.markdown("---")

                # RAW Parts
                st.markdown("### RAW - Raw Material (Sorted by Material Costs)")
                if not st.session_state.filtered_pareto_data['RAW'].empty:
                    df_raw = st.session_state.filtered_pareto_data['RAW'].copy()
                    available_raw_cols = [col for col in filtered_columns if col in df_raw.columns]

                    if available_raw_cols:
                        display_raw = df_raw[available_raw_cols].copy()

                        # Format quantity
                        if 'needed' in display_raw.columns:
                            qty_values = pd.to_numeric(display_raw['needed'], errors='coerce')
                            display_raw['needed'] = qty_values.apply(
                                format_quantity_value
                            )

                        # Format currency
                        for col in ['material_costs', 'outside_costs', 'total_costs']:
                            if col in display_raw.columns:
                                display_raw[col] = display_raw[col].apply(
                                    lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")

                        # Format percentage
                        if 'row_perc' in display_raw.columns:
                            display_raw['row_perc'] = display_raw['row_perc'].apply(
                                lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

                        display_raw = display_raw.rename(columns={'needed': 'Qty'})

                        st.dataframe(display_raw, use_container_width=True, height=300)
                        st.caption(f"Showing {len(display_raw)} parts")
                else:
                    st.info("No RAW parts found")
            else:
                st.info("Run analysis to view filtered data")

        with tab4:
            st.subheader("Cost vs Quantity Bubble Chart")
            st.markdown("**Analysis for codes: 3M, 2B, RAW**")

            # Chart controls
            col1, col2 = st.columns([2, 1])

            with col1:
                scale_option = st.radio(
                    "Select Scale Type:",
                    options=["linear", "log", "sqrt", "focus_cluster"],
                    index=0,
                    horizontal=True,
                    help="Linear: Normal scale | Log: Logarithmic scale | Sqrt: Square root scale | Focus Cluster: Zoom to 95th percentile"
                )
                st.session_state.bubble_scale_option = scale_option

            with col2:
                bubble_size = st.slider(
                    "Bubble Size Multiplier:",
                    min_value=0.01,
                    max_value=1.0,
                    value=0.1,
                    step=0.01,
                    help="Adjust the size of bubbles in the chart"
                )
                st.session_state.bubble_size = bubble_size

            # Generate and display bubble chart
            if st.session_state.df_excel is not None:
                try:
                    bubble_fig = cost_quantity_bubble_chart_interactive(
                        st.session_state.df_excel,
                        scale=st.session_state.bubble_scale_option,
                        code_filter=["3M", "2B", "RAW"],
                        bubble_scale=st.session_state.bubble_size
                    )
                    st.plotly_chart(bubble_fig, use_container_width=True)

                    # Add explanation
                    st.markdown("""
                    **Chart Interpretation:**
                    - **Bubble Size**: Represents the total cost
                    - **X-axis**: Needed quantity of parts
                    - **Y-axis**: Total cost per part
                    - **Colors**: Different codes (3M, 2B, RAW)
                    - **Top-Left**: High cost, low quantity (premium/specialty items)
                    - **Bottom-Right**: Low cost, high quantity (bulk items)
                    """)
                except Exception as e:
                    st.error(f"Error generating bubble chart: {str(e)}")
            else:
                st.info("Run analysis to view bubble chart")
    else:
        st.info("Click 'Run Recommended Analysis' or configure and run 'Custom Analysis' to view results")

