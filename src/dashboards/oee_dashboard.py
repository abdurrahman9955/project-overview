# src/dashboards/oee_dashboard.py

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import dash_bootstrap_components as dbc

# Import generic UI components
from utils.ui_components import create_kpi_card, create_filter_card

# --- OEE Layout Function ---
def create_oee_layout(oee_kpis, oee_augmented_data):
    return html.Div([
        html.H3("Overall Equipment Effectiveness Overview", className="text-center my-4"),
        html.P("Monitor and improve manufacturing productivity by tracking OEE components (Availability, Performance, Quality) and downtime costs.", className="text-center text-muted"),

        # KPIs for OEE
        dbc.Row([
            dbc.Col(create_kpi_card("Average OEE", oee_kpis.get('Average OEE (%)'), is_percentage=True), md=4),
            dbc.Col(create_kpi_card("Average TEEP", oee_kpis.get('Average TEEP (%)'), is_percentage=True), md=4),
            dbc.Col(create_kpi_card("Avg Downtime Cost/Min", oee_kpis.get('Average Downtime Cost per Minute (£)'), unit="£"), md=4)
        ], className="mb-4 justify-content-center"),

        # Filters for OEE
        create_filter_card([
            dbc.Row([
                dbc.Col([
                    html.Label("Select Date Range:"),
                    dcc.DatePickerRange(
                        id='oee-date-range-filter',
                        # Ensure data exists before trying to get min/max dates
                        start_date=oee_augmented_data['monthly_oee_trends']['Month'].min().date() if (oee_augmented_data and oee_augmented_data['monthly_oee_trends'] is not None and not oee_augmented_data['monthly_oee_trends'].empty) else None,
                        end_date=oee_augmented_data['monthly_oee_trends']['Month'].max().date() if (oee_augmented_data and oee_augmented_data['monthly_oee_trends'] is not None and not oee_augmented_data['monthly_oee_trends'].empty) else None,
                        display_format='MMM DD, YYYY',
                    )
                ], md=4),
                dbc.Col([
                    html.Label("Select Shift:"),
                    dcc.Dropdown(
                        id='oee-shift-filter',
                        options=[{'label': 'All Shifts', 'value': 'All Shifts'}], # Dummy for now, as no shift data in CSV
                        value='All Shifts', # Default to 'All Shifts'
                        multi=False
                    )
                ], md=4),
                dbc.Col([ # NEW: Downtime Reason Filter
                    html.Label("Select Downtime Reason:"),
                    dcc.Dropdown(
                        id='oee-downtime-reason-filter',
                        options=[], # Options populated by callback
                        value='All Reasons', # Default value to show all results initially
                        placeholder="All Reasons",
                        multi=False
                    )
                ], md=4),
            ])
        ]),
        
        # OEE Visualizations
        dbc.Row([
            dbc.Col(dcc.Graph(id='oee-trend-chart'), md=8),
            dbc.Col(dcc.Graph(id='oee-components-gauge'), md=4), # Gauge for latest OEE components
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(html.H4("Downtime Cost Analysis", className="mt-4 text-center"), width=12),
            dbc.Col(html.Div(id='oee-downtime-table-container'), width=12) 
        ])
    ], className="p-4")

# --- OEE Callbacks ---

def register_oee_callbacks(app):
    # Callback to populate Downtime Reason filter options dynamically for OEE dashboard
    @app.callback(
        Output('oee-downtime-reason-filter', 'options'),
        [Input('stored-downtime-data', 'data')]
    )
    def set_oee_downtime_reason_options(jsonified_data):
        if jsonified_data is None:
            return []
        
        df = pd.read_json(jsonified_data, orient='split')
        if df.empty:
            return []

        all_reasons = set()
        for reasons_str in df['Root Cause (Top 3)'].dropna():
            parts = [part.strip().split('(')[0].strip() for part in reasons_str.split(',')]
            for part in parts:
                if part:
                    all_reasons.add(part)
        
        options = [{'label': 'All Reasons', 'value': 'All Reasons'}]
        options.extend([{'label': reason, 'value': reason} for reason in sorted(list(all_reasons))])
        return options

    # Callback for OEE Trend Chart
    @app.callback(
        Output('oee-trend-chart', 'figure'),
        [Input('stored-oee-data', 'data'),
         Input('oee-date-range-filter', 'start_date'),
         Input('oee-date-range-filter', 'end_date')]
    )
    def update_oee_trend_chart(jsonified_data, start_date, end_date):
        if jsonified_data is None:
            return {}
        
        df = pd.read_json(jsonified_data, orient='split')
        if df.empty:
            return {}
        
        df['Month'] = pd.to_datetime(df['Month'])
        
        df_filtered = df.copy()
        if start_date and end_date:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df_filtered = df[(df['Month'] >= start_dt) & 
                             (df['Month'] <= end_dt)]
        
        if df_filtered.empty:
            return go.Figure().update_layout(title="No data for selected filter.")
        
        fig = px.line(
            df_filtered,
            x='Month',
            y=['OEE (%)', 'Availability (%)', 'Performance (%)', 'Quality (%)'],
            title='Monthly OEE and Components Trend',
            labels={
                'value': 'Percentage (%)', 
                'variable': 'Metric',
                'Month': 'Month'
            },
            markers=True,
            height=450
        )
        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        fig.update_xaxes(dtick="M1", tickformat="%b\n%Y")
        return fig

    # Callback for OEE Components Gauge
    @app.callback(
        Output('oee-components-gauge', 'figure'),
        [Input('stored-oee-data', 'data'),
         Input('oee-date-range-filter', 'end_date')] 
    )
    def update_oee_components_gauge(jsonified_data, end_date):
        if jsonified_data is None:
            return {}
        
        df = pd.read_json(jsonified_data, orient='split')
        if df.empty:
            return {}
        
        df['Month'] = pd.to_datetime(df['Month'])
        
        latest_month_data = pd.DataFrame()
        if end_date:
            end_dt = pd.to_datetime(end_date)
            latest_month_data = df[df['Month'] <= end_dt].sort_values(by='Month', ascending=False).head(1)
        else:
            latest_month_data = df.sort_values(by='Month', ascending=False).head(1)
            
        if latest_month_data.empty:
            return go.Figure().update_layout(title="No data for gauge.")

        oee_val = latest_month_data['OEE (%)'].iloc[0] if 'OEE (%)' in latest_month_data.columns else None
        availability_val = latest_month_data['Availability (%)'].iloc[0] if 'Availability (%)' in latest_month_data.columns else None
        performance_val = latest_month_data['Performance (%)'].iloc[0] if 'Performance (%)' in latest_month_data.columns else None
        quality_val = latest_month_data['Quality (%)'].iloc[0] if 'Quality (%)' in latest_month_data.columns else None

        fig = go.Figure()

        if oee_val is not None:
            fig.add_trace(go.Indicator(
                mode = "gauge+number",
                value = oee_val * 100, # Convert to 0-100 scale for gauge
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "<b>OEE (%)</b><br><span style='font-size:0.8em;color:gray'>Current Metric</span>"},
                gauge = {
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "green"},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 60], 'color': 'lightgray'},
                        {'range': [60, 80], 'color': 'gray'}],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 85}} # Target OEE
            ))
            
        annotations = []
        if availability_val is not None and performance_val is not None and quality_val is not None:
            annotations.append(dict(
                x=0.5, y=0.1, xref="paper", yref="paper",
                text=f"Avail: {availability_val*100:.2f}% | Perf: {performance_val*100:.2f}% | Qual: {quality_val*100:.2f}%",
                showarrow=False, font=dict(size=12, color="gray")
            ))
            
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10),
                          annotations=annotations)
        return fig


    # Callback for OEE Downtime Cost Analysis Table (reacts to downtime reason filter)
    @app.callback(
        Output('oee-downtime-table-container', 'children'),
        [Input('stored-downtime-data', 'data'),
         Input('oee-downtime-reason-filter', 'value')]
    )
    def update_oee_downtime_table(jsonified_data, selected_reason):
        if jsonified_data is None:
            return html.Div("No Downtime Cost Analysis Data Available.")
        
        df = pd.read_json(jsonified_data, orient='split')
        if df.empty:
            return html.Div("No Downtime Cost Analysis Data Available.")
        
        filtered_df = df.copy()
        if selected_reason and selected_reason != 'All Reasons':
            filtered_df = df[df['Root Cause (Top 3)'].astype(str).str.strip().str.contains(selected_reason.strip(), case=False, na=False)]

        if filtered_df.empty:
            return html.Div(f"No data for selected downtime reason: {selected_reason}.")

        df_display = filtered_df.copy()
        if 'Cost/Min (£)' in df_display.columns:
            df_display['Cost/Min (£)'] = df_display['Cost/Min (£)'].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) else "N/A")
        if 'Total Cost (£)' in df_display.columns:
            df_display['Total Cost (£)'] = df_display['Total Cost (£)'].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) else "N/A")

        return dbc.Table.from_dataframe(df_display, striped=True, bordered=True, hover=True, className="mt-2")