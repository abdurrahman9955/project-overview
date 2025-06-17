# src/dashboards/mfg_cost_dashboard.py

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import dash_bootstrap_components as dbc

# Import generic UI components
from utils.ui_components import create_kpi_card, create_filter_card

# --- Manufacturing Cost Layout Function ---
def create_mfg_cost_layout(mfg_cost_kpis, mfg_cost_augmented_data):
    return html.Div([
        html.H3("Manufacturing Cost per Unit Overview", className="text-center my-4"),
        html.P("Track the efficiency of material usage, labor, and overhead to understand and optimize the total cost of production per unit.", className="text-center text-muted"),

        # KPIs for Manufacturing Cost
        dbc.Row([
            dbc.Col(create_kpi_card("Avg Total Cost/Unit", mfg_cost_kpis.get('Average Total Cost per Unit (£)'), unit="£"), md=4),
            dbc.Col(create_kpi_card("Avg Labor Efficiency", mfg_cost_kpis.get('Average Labor Efficiency (%)'), is_percentage=True), md=4),
            dbc.Col(create_kpi_card("Avg Material Yield", mfg_cost_kpis.get('Average Material Yield (%)'), is_percentage=True), md=4),
            dbc.Col(create_kpi_card("Latest Cost Variance", mfg_cost_kpis.get('Latest Cost Variance (£)'), unit="£"), md=4),
        ], className="mb-4 justify-content-center"),

        # Filters for Manufacturing Cost
        create_filter_card([
            dbc.Row([
                dbc.Col([
                    html.Label("Select Month:"),
                    dcc.Dropdown(
                        id='mfg-cost-month-filter',
                        options=[{'label': month.strftime('%B'), 'value': month.strftime('%B')} 
                                 for month in mfg_cost_augmented_data['total_mfg_cost_trends'].index] if mfg_cost_augmented_data and mfg_cost_augmented_data['total_mfg_cost_trends'] is not None else [],
                        value=mfg_cost_augmented_data['total_mfg_cost_trends'].index[0].strftime('%B') if (mfg_cost_augmented_data and mfg_cost_augmented_data['total_mfg_cost_trends'] is not None and not mfg_cost_augmented_data['total_mfg_cost_trends'].empty) else None,
                        multi=False
                    )
                ], md=6),
                dbc.Col([
                    html.Label("Select Cost Category:"),
                    dcc.Dropdown(
                        id='mfg-cost-category-filter',
                        options=[{'label': col, 'value': col} 
                                 for col in ['Total Direct Material Cost (£)', 'Total Direct Labor Cost (£)', 'Total Manufacturing Overhead (£)']] if mfg_cost_augmented_data and mfg_cost_augmented_data['total_mfg_cost_trends'] is not None else [],
                        value='Total Direct Material Cost (£)',
                        multi=False
                    )
                ], md=6),
            ])
        ]),
        
        # Manufacturing Cost Visualizations
        dbc.Row([
            dbc.Col(dcc.Graph(id='mfg-cost-trend-chart'), md=6),
            dbc.Col(dcc.Graph(id='mfg-cost-breakdown-pie'), md=6),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(html.H4("Cost Variance Analysis", className="mt-4 text-center"), width=12),
            dbc.Col(html.Div(id='mfg-cost-variance-table-container'), width=12) 
        ])
    ], className="p-4")

# --- Manufacturing Cost Callbacks ---

def register_mfg_cost_callbacks(app):
    # Callback for Manufacturing Cost Trend Chart
    @app.callback(
        Output('mfg-cost-trend-chart', 'figure'),
        [Input('stored-mfg-cost-data', 'data'),
         Input('mfg-cost-category-filter', 'value')]
    )
    def update_mfg_cost_trend_chart(jsonified_data, selected_category):
        if jsonified_data is None:
            return {}
        
        df = pd.read_json(jsonified_data, orient='split')
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        if df.empty or selected_category not in df.columns:
            return {}

        fig = px.line(
            df,
            x=df.index, # Month is the index
            y=selected_category,
            title=f'Monthly Trend: {selected_category}',
            labels={
                df.index.name: 'Month',
                selected_category: 'Cost (£)'
            },
            markers=True,
            height=400
        )
        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        fig.update_xaxes(dtick="M1", tickformat="%b\n%Y")
        return fig

    # Callback for Manufacturing Cost Breakdown Pie Chart
    @app.callback(
        Output('mfg-cost-breakdown-pie', 'figure'),
        [Input('stored-mfg-cost-data', 'data'),
         Input('mfg-cost-month-filter', 'value')]
    )
    def update_mfg_cost_breakdown_pie(jsonified_data, selected_month):
        if jsonified_data is None:
            return {}
        
        df = pd.read_json(jsonified_data, orient='split')
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        if df.empty:
            return {}
        
        df_filtered = df[df.index.strftime('%B') == selected_month]

        if df_filtered.empty:
            return {}
        
        materials_cost = df_filtered['Total Direct Material Cost (£)'].iloc[0] if 'Total Direct Material Cost (£)' in df_filtered.columns else 0
        labor_cost = df_filtered['Total Direct Labor Cost (£)'].iloc[0] if 'Total Direct Labor Cost (£)' in df_filtered.columns else 0
        overhead_cost = df_filtered['Total Manufacturing Overhead (£)'].iloc[0] if 'Total Manufacturing Overhead (£)' in df_filtered.columns else 0

        costs = [materials_cost, labor_cost, overhead_cost]
        labels = ['Materials', 'Labor', 'Overhead']

        fig = px.pie(
            names=labels,
            values=costs,
            title=f'Cost Components Breakdown for {selected_month}',
            hole=0.3,
            height=400,
            color_discrete_sequence=px.colors.sequential.RdBu 
        )
        fig.update_traces(textinfo='percent+label', marker=dict(line=dict(color='#000000', width=1)))
        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        return fig

    # Callback for Manufacturing Cost Variance Table
    @app.callback(
        Output('mfg-cost-variance-table-container', 'children'),
        [Input('stored-cost-variance-data', 'data')]
    )
    def update_mfg_cost_variance_table(jsonified_data):
        if jsonified_data is None:
            return html.Div("No Cost Variance Data Available.")
        
        df = pd.read_json(jsonified_data, orient='split')
        if df.empty:
            return html.Div("No Cost Variance Data Available.")
        
        df_display = df.copy()
        if 'Variance (%)' in df_display.columns:
            df_display['Variance (%)'] = df_display['Variance (%)'].apply(lambda x: f"{x * 100:.2f}%" if pd.notna(x) else "N/A")
        if 'Actual' in df_display.columns:
            df_display['Actual'] = df_display['Actual'].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) else "N/A")
        if 'Budget' in df_display.columns:
            df_display['Budget'] = df_display['Budget'].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) else "N/A")
        if 'Variance (£)' in df_display.columns:
            df_display['Variance (£)'] = df_display['Variance (£)'].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) else "N/A")

        return dbc.Table.from_dataframe(df_display, striped=True, bordered=True, hover=True, className="mt-2")