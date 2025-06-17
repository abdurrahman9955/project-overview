# src/dashboards/copq_dashboard.py

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import dash_bootstrap_components as dbc

# Import generic UI components
from utils.ui_components import create_kpi_card, create_filter_card

# --- COPQ Layout Function ---
def create_copq_layout(copq_kpis, copq_augmented_data):
    return html.Div([
        html.H3("Cost of Poor Quality Overview", className="text-center my-4"),
        html.P("This dashboard helps to identify and quantify the costs associated with quality failures, providing insights into areas for improvement.", className="text-center text-muted"),
        
        # KPIs for COPQ
        dbc.Row([
            dbc.Col(create_kpi_card("Total COPQ", copq_kpis.get('Total COPQ (£)'), unit="£"), md=4),
            dbc.Col(create_kpi_card("Defect Rate", copq_kpis.get('Defect Rate (PPM)'), unit=" PPM"), md=4),
            dbc.Col(create_kpi_card("Scrap % of Revenue", copq_kpis.get('Scrap Cost as % of Revenue'), is_percentage=True), md=4),
            dbc.Col(create_kpi_card("Rework % of Revenue", copq_kpis.get('Rework Cost as % of Revenue'), is_percentage=True), md=4),
            dbc.Col(create_kpi_card("Warranty % of Revenue", copq_kpis.get('Warranty Cost as % of Revenue'), is_percentage=True), md=4),
        ], className="mb-4 justify-content-center"),

        # Filters for COPQ
        create_filter_card([
            dbc.Row([
                dbc.Col([
                    html.Label("Select Month for Trend:"),
                    dcc.Dropdown(
                        id='copq-month-filter',
                        # Use iso format for value to ensure consistent date parsing in callback
                        options=[{'label': month.strftime('%B'), 'value': month.strftime('%Y-%m-01')} 
                                 for month in copq_augmented_data['monthly_copq_tracking']['Month']] if copq_augmented_data and copq_augmented_data['monthly_copq_tracking'] is not None else [],
                        value=None, # Default to None to show full trend initially
                        placeholder="All Months (Full Trend)",
                        multi=False
                    ),
                ], md=6),
                dbc.Col([
                    html.Label("Select Defect Type for Table:"),
                    dcc.Dropdown(
                        id='copq-defect-type-filter',
                        options=[{'label': dt, 'value': dt} 
                                 for dt in (copq_augmented_data['defect_categories']['Defect Type'].unique() if copq_augmented_data and copq_augmented_data['defect_categories'] is not None else [])],
                        value='Total', # Default to Total to show all data initially
                        multi=False
                    ),
                ], md=6),
            ])
        ]),
        
        # COPQ Visualizations
        dbc.Row([
            dbc.Col(dcc.Graph(id='copq-cost-breakdown-chart'), md=6),
            dbc.Col(dcc.Graph(id='copq-monthly-trend-chart'), md=6),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(html.H4("Defect Categories Breakdown", className="mt-4 text-center"), width=12),
            dbc.Col(html.Div(id='copq-defect-table-container'), width=12) 
        ]),
        dbc.Row([ # New Row for Defect Type Associated Cost Chart
            dbc.Col(html.H4("Associated Cost by Selected Defect Type", className="mt-4 text-center"), width=12),
            dbc.Col(dcc.Graph(id='copq-defect-type-cost-chart'), md=12), # New Chart for Defect Type cost
        ])
    ], className="p-4")

# --- COPQ Callbacks ---

def register_copq_callbacks(app):
    # Callback for COPQ Cost Breakdown Chart
    @app.callback(
        Output('copq-cost-breakdown-chart', 'figure'),
        [Input('stored-copq-breakdown-data', 'data')]
    )
    def update_copq_breakdown_chart(jsonified_data):
        if jsonified_data is None:
            return {}
        
        df = pd.read_json(jsonified_data, orient='records')
        if df.empty:
            return {}

        df_filtered = df[df['Category'].astype(str).str.strip().str.lower() != 'total']

        fig = px.bar(
            df_filtered,
            x='Category',
            y='Cost (£)',
            title='COPQ Cost Breakdown',
            color='Category',
            color_discrete_map={
                'Scrap': '#EF4444', # red-500
                'Rework': '#F97316', # orange-500
                'Warranty': '#F59E0B' # amber-500
            },
            labels={'Cost (£)': 'Cost (£)', 'Category': 'COPQ Category'},
            height=400
        )
        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        return fig

    # Callback for COPQ Monthly Trend Chart (now reacts to month filter)
    @app.callback(
        Output('copq-monthly-trend-chart', 'figure'),
        [Input('stored-copq-data', 'data'),
         Input('copq-month-filter', 'value')] # Month filter input
    )
    def update_copq_monthly_trend_chart(jsonified_data, selected_month_iso):
        if jsonified_data is None:
            return {}
        
        df = pd.read_json(jsonified_data, orient='records')
        df['Month'] = pd.to_datetime(df['Month']) # Ensure Month is datetime

        if df.empty:
            return {}
        
        filtered_df = df.copy()
        
        if selected_month_iso: # If a month is selected (value is YYYY-MM-DD string)
            selected_month_dt = pd.to_datetime(selected_month_iso)
            # Filter by year and month
            filtered_df = df[
                (df['Month'].dt.year == selected_month_dt.year) &
                (df['Month'].dt.month == selected_month_dt.month)
            ]
            title = f"COPQ for {selected_month_dt.strftime('%B %Y')}"
            
            # Use px.bar for a single month
            fig = px.bar(
                filtered_df,
                x='Month',
                y='COPQ (£)',
                title=title,
                labels={'COPQ (£)': 'COPQ (£)', 'Month': 'Month'},
                height=400
            )
        else: # No month selected, show full trend
            title = "Monthly COPQ Trend"
            # Use px.line for trend over time, KEEP markers=True
            fig = px.line(
                filtered_df,
                x='Month',
                y='COPQ (£)',
                title=title,
                labels={'COPQ (£)': 'COPQ (£)', 'Month': 'Month'},
                markers=True,
                height=400
            )
            
        if filtered_df.empty:
            return go.Figure().update_layout(title="No data for selected filter.")

        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        fig.update_xaxes(dtick="M1", tickformat="%b\n%Y") # Format x-axis for monthly display
        return fig

    # Callback for COPQ Defect Categories Breakdown Table
    @app.callback(
        Output('copq-defect-table-container', 'children'), # Output to the Div, not direct table
        [Input('stored-copq-defect-data', 'data'),
         Input('copq-defect-type-filter', 'value')]
    )
    def update_copq_defect_table(jsonified_data, selected_defect_type):
        if jsonified_data is None:
            return html.Div("No Defect Categories Data Available.")
        
        df = pd.read_json(jsonified_data, orient='records')
        if df.empty:
            return html.Div("No Defect Categories Data Available.")
        
        filtered_df = df.copy()
        if selected_defect_type and selected_defect_type != 'Total':
            filtered_df = df[df['Defect Type'] == selected_defect_type]

        if filtered_df.empty:
            return html.Div(f"No data for selected defect type: {selected_defect_type}.")

        df_display = filtered_df.copy()
        if '% of Total Defects' in df_display.columns:
            df_display['% of Total Defects'] = df_display['% of Total Defects'].apply(lambda x: f"{x * 100:.2f}%" if pd.notna(x) else "N/A")
        df_display['Associated Cost (£)'] = df_display['Associated Cost (£)'].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) else "N/A")

        return dbc.Table.from_dataframe(df_display, striped=True, bordered=True, hover=True, className="mt-2")

    # NEW Callback for COPQ Defect Type Associated Cost Chart
    @app.callback(
        Output('copq-defect-type-cost-chart', 'figure'),
        [Input('stored-copq-defect-data', 'data'),
         Input('copq-defect-type-filter', 'value')]
    )
    def update_copq_defect_type_cost_chart(jsonified_data, selected_defect_type):
        if jsonified_data is None:
            return {}

        df = pd.read_json(jsonified_data, orient='records')
        if df.empty:
            return {}

        if selected_defect_type == 'Total':
            df_plot = df[df['Defect Type'] != 'Total']
            title_suffix = "All Defect Types"
        else:
            df_plot = df[df['Defect Type'] == selected_defect_type]
            title_suffix = f"'{selected_defect_type}'"
        
        if df_plot.empty:
            return go.Figure().update_layout(title="No data for selected defect type.")

        fig = px.bar(
            df_plot,
            x='Defect Type',
            y='Associated Cost (£)',
            title=f'Associated Cost for {title_suffix}',
            labels={'Associated Cost (£)': 'Cost (£)', 'Defect Type': 'Defect Type'},
            color='Defect Type',
            height=400
        )
        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        return fig

       