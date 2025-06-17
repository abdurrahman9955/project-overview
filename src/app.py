# src/app.py

import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os
import dash_bootstrap_components as dbc

# Import our custom data processing and KPI calculation functions
from data_processor import load_and_process_copq_data, load_and_process_oee_data, load_and_process_mfg_cost_data
from kpi_calculations import calculate_copq_kpis, calculate_oee_kpis, calculate_mfg_cost_kpis

# Import dashboard layouts and callbacks
from dashboards.copq_dashboard import create_copq_layout, register_copq_callbacks
from dashboards.oee_dashboard import create_oee_layout, register_oee_callbacks
from dashboards.mfg_cost_dashboard import create_mfg_cost_layout, register_mfg_cost_callbacks
from dashboards.ai_insights_dashboard import create_ai_insights_layout, register_ai_insights_callbacks

# Import generic UI components (though not directly used in app.py layout, good to know where they are)
from utils.ui_components import create_kpi_card, create_filter_card

# --- Data Loading and Initial KPI Calculation ---
# Define file paths
current_dir = os.path.dirname(__file__)
data_dir = os.path.join(current_dir, '..', 'data')

COPQ_FILE = os.path.join(data_dir, 'COPQ_Dummy_Data.csv')
OEE_FILE = os.path.join(data_dir, 'OEE_Dummy_Data.csv')
MFG_COST_FILE = os.path.join(data_dir, 'Manufacturing_Cost_per_Unit_Calculator.csv')

# Load and process all data
copq_raw_data = load_and_process_copq_data(COPQ_FILE)
oee_raw_data = load_and_process_oee_data(OEE_FILE)
mfg_cost_raw_data = load_and_process_mfg_cost_data(MFG_COST_FILE)

# Calculate initial KPIs and get augmented dataframes
copq_kpis, copq_augmented_data = calculate_copq_kpis(copq_raw_data) if copq_raw_data else ({}, {})
oee_kpis, oee_augmented_data = calculate_oee_kpis(oee_raw_data) if oee_raw_data else ({}, {})
mfg_cost_kpis, mfg_cost_augmented_data = calculate_mfg_cost_kpis(mfg_cost_raw_data) if mfg_cost_raw_data else ({}, {})

# --- Dash App Setup ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP]) 

# --- Dash App Layout ---
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col(html.H1("Manufacturing KPI Dashboards", className="text-center text-primary my-4"), width=12)
    ]),

    # Tabs for each Dashboard
    dbc.Tabs(id="tabs-main", active_tab="tab-copq", children=[
        dbc.Tab(label="COPQ Dashboard", tab_id="tab-copq", children=[
            create_copq_layout(copq_kpis, copq_augmented_data)
        ]),

        dbc.Tab(label="OEE Dashboard", tab_id="tab-oee", children=[
            create_oee_layout(oee_kpis, oee_augmented_data)
        ]),

        dbc.Tab(label="Manufacturing Cost per Unit Dashboard", tab_id="tab-mfg-cost", children=[
            create_mfg_cost_layout(mfg_cost_kpis, mfg_cost_augmented_data)
        ]),
        
        dbc.Tab(label="AI Insights", tab_id="tab-ai-insights", children=[
            create_ai_insights_layout()
        ])
    ], className="mt-4"),
    
    # Hidden Div to store processed data for callbacks
    dcc.Store(id='stored-copq-data', data=copq_augmented_data['monthly_copq_tracking'].to_json(date_format='iso', orient='records') if copq_augmented_data and copq_augmented_data['monthly_copq_tracking'] is not None else None),
    dcc.Store(id='stored-copq-breakdown-data', data=copq_augmented_data['copq_breakdown'].to_json(orient='records') if copq_augmented_data and copq_augmented_data['copq_breakdown'] is not None else None),
    dcc.Store(id='stored-copq-defect-data', data=copq_augmented_data['defect_categories'].to_json(orient='records') if copq_augmented_data and copq_augmented_data['defect_categories'] is not None else None),

    dcc.Store(id='stored-oee-data', data=oee_augmented_data['monthly_oee_trends'].to_json(date_format='iso', orient='split') if oee_augmented_data and oee_augmented_data['monthly_oee_trends'] is not None else None),
    dcc.Store(id='stored-downtime-data', data=oee_augmented_data['downtime_cost_analysis'].to_json(date_format='iso', orient='split') if oee_augmented_data and oee_augmented_data['downtime_cost_analysis'] is not None else None),

    dcc.Store(id='stored-mfg-cost-data', data=mfg_cost_augmented_data['total_mfg_cost_trends'].to_json(date_format='iso', orient='split') if mfg_cost_augmented_data and mfg_cost_augmented_data['total_mfg_cost_trends'] is not None else None),
    dcc.Store(id='stored-efficiency-data', data=mfg_cost_augmented_data['efficiency_trends'].to_json(date_format='iso', orient='split') if mfg_cost_augmented_data and mfg_cost_augmented_data['efficiency_trends'] is not None else None),
    dcc.Store(id='stored-cost-variance-data', data=mfg_cost_augmented_data['cost_variance_analysis'].to_json(orient='split') if mfg_cost_augmented_data and mfg_cost_augmented_data['cost_variance_analysis'] is not None else None),

], fluid=True, className="my-4")


# --- Register Callbacks from all Dashboards ---
register_copq_callbacks(app)
register_oee_callbacks(app)
register_mfg_cost_callbacks(app)
register_ai_insights_callbacks(app) # Registering the placeholder callback function

# Run the app
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))  
    app.run(host='0.0.0.0', port=port, debug=True)
