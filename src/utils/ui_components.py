# src/utils/ui_components.py

from dash import html
import dash_bootstrap_components as dbc

def create_kpi_card(title, value, unit="", is_percentage=False):
    """Creates a standardized KPI display card."""
    display_value = f"{value:,.2f}{unit}" if isinstance(value, (int, float)) and value is not None else "N/A"
    if is_percentage and isinstance(value, (int, float)) and value is not None:
        display_value = f"{value * 100:.2f}%"
        
    return dbc.Card(
        dbc.CardBody([
            html.H5(title, className="card-title text-muted"),
            html.H2(display_value, className="card-text text-primary")
        ]),
        className="text-center my-2 shadow-sm rounded-lg"
    )

def create_filter_card(children):
    """Creates a standardized filter section card."""
    return dbc.Card(
        dbc.CardBody(children),
        className="mb-4 shadow-sm rounded-lg"
    )