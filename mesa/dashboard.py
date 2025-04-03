import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from mesa_model import ShipPortModel
from port import Port
import json
from collections import defaultdict

# Initialize the app with a modern theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# Initialize the model
model = ShipPortModel(width=100, height=100, num_ships=300)

# Run a few steps to get some data
# for _ in range(10):
#     model.step()

# Store historical data
historical_data = {
    'steps': [],
    'global': {
        'total_ships': [],
        'scrubber_ships': [],
        'non_scrubber_ships': [],
        'scrubber_trails': [],
        'avg_penalty': [],
        'total_revenue': []
    },
    'ports': defaultdict(lambda: {
        'revenue': [],
        'occupancy': [],
        'docked_ships': []
    })
}

# Function to collect data from the model
def collect_model_data():
    # Global statistics
    global_stats = {
        'step': model.schedule.steps,
        'ships': {
            'total': sum(1 for a in model.schedule.agents if hasattr(a, 'ship_type')),
            'scrubber': sum(1 for a in model.schedule.agents if hasattr(a, 'is_scrubber') and a.is_scrubber),
            'non_scrubber': sum(1 for a in model.schedule.agents if hasattr(a, 'is_scrubber') and not a.is_scrubber),
            'by_type': {}
        },
        'environment': {
            'scrubber_trails': sum(1 for a in model.schedule.agents if hasattr(a, 'water_units')),
            'avg_penalty': model.get_average_penalty()
        },
        'economics': {
            'total_revenue': sum(a.revenue for a in model.schedule.agents if hasattr(a, 'revenue'))
        }
    }
    
    # Count ships by type
    ship_types = {}
    for agent in model.schedule.agents:
        if hasattr(agent, 'ship_type'):
            ship_type = agent.ship_type
            ship_types[ship_type] = ship_types.get(ship_type, 0) + 1
    global_stats['ships']['by_type'] = ship_types
    
    # Per-port data
    port_data = {}
    for agent in model.schedule.agents:
        if hasattr(agent, 'name') and hasattr(agent, 'port_capacity'):
            port_id = agent.unique_id
            
            # Count docked ships by type
            docked_by_type = {}
            for ship in agent.docked_ships:
                ship_type = ship.ship_type
                docked_by_type[ship_type] = docked_by_type.get(ship_type, 0) + 1
            
            port_data[port_id] = {
                'name': agent.name,
                'location': (agent.lat, agent.lon),
                'capacity': {
                    'current': agent.current_capacity,
                    'maximum': agent.port_capacity,
                    'occupancy_rate': agent.current_capacity / agent.port_capacity if agent.port_capacity > 0 else 0
                },
                'docked_ships': {
                    'total': len(agent.docked_ships),
                    'by_type': docked_by_type
                },
                'revenue': agent.revenue,
                'allow_scrubber': agent.allow_scrubber
            }
    
    # Update historical data
    historical_data['steps'].append(model.schedule.steps)
    historical_data['global']['total_ships'].append(global_stats['ships']['total'])
    historical_data['global']['scrubber_ships'].append(global_stats['ships']['scrubber'])
    historical_data['global']['non_scrubber_ships'].append(global_stats['ships']['non_scrubber'])
    historical_data['global']['scrubber_trails'].append(global_stats['environment']['scrubber_trails'])
    historical_data['global']['avg_penalty'].append(global_stats['environment']['avg_penalty'])
    historical_data['global']['total_revenue'].append(global_stats['economics']['total_revenue'])
    
    for port_id, data in port_data.items():
        if port_id not in historical_data['ports']:
            historical_data['ports'][port_id] = {
                'revenue': [],
                'occupancy': [],
                'docked_ships': []
            }
        historical_data['ports'][port_id]['revenue'].append(data['revenue'])
        historical_data['ports'][port_id]['occupancy'].append(data['capacity']['occupancy_rate'])
        historical_data['ports'][port_id]['docked_ships'].append(data['docked_ships']['total'])
    
    return global_stats, port_data

# Get initial data
global_stats, port_data = collect_model_data()

# Create DataFrames for visualization
def create_dataframes(global_stats, port_data):
    # Ship types DataFrame: force columns even if no items exist
    ship_types_list = [
        {'Type': ship_type, 'Count': count}
        for ship_type, count in global_stats['ships']['by_type'].items()
    ]
    ship_types_df = pd.DataFrame(ship_types_list, columns=['Type', 'Count'])
    
    # Scrubber status DataFrame
    scrubber_df = pd.DataFrame([
        {'Status': 'Scrubber', 'Count': global_stats['ships']['scrubber']},
        {'Status': 'Non-Scrubber', 'Count': global_stats['ships']['non_scrubber']}
    ])
    
    # Port DataFrame
    port_df = pd.DataFrame([
        {
            'Port': data['name'],
            'Current Capacity': data['capacity']['current'],
            'Maximum Capacity': data['capacity']['maximum'],
            'Occupancy Rate': data['capacity']['occupancy_rate'],
            'Docked Ships': data['docked_ships']['total'],
            'Revenue': data['revenue'],
            'Allow Scrubber': 'Yes' if data['allow_scrubber'] else 'No',
            'Latitude': data['location'][0],
            'Longitude': data['location'][1]
        }
        for port_id, data in port_data.items()
    ])
    
    # Create a DataFrame for each port's docked ship types
    port_ship_types = []
    for port_id, data in port_data.items():
        for ship_type, count in data['docked_ships']['by_type'].items():
            port_ship_types.append({
                'Port': data['name'],
                'Ship Type': ship_type,
                'Count': count
            })
    
    port_ship_types_df = (pd.DataFrame(port_ship_types, columns=['Port', 'Ship Type', 'Count'])
                          if port_ship_types else pd.DataFrame(columns=['Port', 'Ship Type', 'Count']))
    
    return ship_types_df, scrubber_df, port_df, port_ship_types_df
ship_types_df, scrubber_df, port_df, port_ship_types_df = create_dataframes(global_stats, port_data)

# Create time series DataFrames
def create_time_series_dataframes():
    # Global time series
    if len(historical_data['steps']) > 0:
        global_ts_df = pd.DataFrame({
            'Step': historical_data['steps'],
            'Total Ships': historical_data['global']['total_ships'],
            'Scrubber Ships': historical_data['global']['scrubber_ships'],
            'Non-Scrubber Ships': historical_data['global']['non_scrubber_ships'],
            'Scrubber Trails': historical_data['global']['scrubber_trails'],
            'Average Penalty': historical_data['global']['avg_penalty'],
            'Total Revenue': historical_data['global']['total_revenue']
        })
    else:
        global_ts_df = pd.DataFrame(columns=['Step', 'Total Ships', 'Scrubber Ships', 'Non-Scrubber Ships', 
                                            'Scrubber Trails', 'Average Penalty', 'Total Revenue'])
    
    # Port time series
    port_ts_data = []
    for port_id, data in historical_data['ports'].items():
        port_name = next((p['name'] for p_id, p in port_data.items() if int(p_id) == int(port_id)), f"Port {port_id}")
        for i, step in enumerate(historical_data['steps']):
            if i < len(data['revenue']):
                port_ts_data.append({
                    'Step': step,
                    'Port': port_name,
                    'Revenue': data['revenue'][i],
                    'Occupancy Rate': data['occupancy'][i],
                    'Docked Ships': data['docked_ships'][i]
                })
    
    port_ts_df = pd.DataFrame(port_ts_data) if port_ts_data else pd.DataFrame(columns=['Step', 'Port', 'Revenue', 'Occupancy Rate', 'Docked Ships'])
    
    return global_ts_df, port_ts_df

global_ts_df, port_ts_df = create_time_series_dataframes()

simulation_settings = dbc.Accordion(
    [
        dbc.AccordionItem(
            dbc.Row([
                dbc.Col([
                    dbc.Label("Width"),
                    dbc.Input(id="sim-width", type="number", value=100, min=10, max=500, step=10)
                ], width=3),
                dbc.Col([
                    dbc.Label("Height"),
                    dbc.Input(id="sim-height", type="number", value=100, min=10, max=500, step=10)
                ], width=3),
                dbc.Col([
                    dbc.Label("Number of Ships"),
                    dbc.Input(id="sim-num-ships", type="number", value=100, min=1, step=1)
                ], width=3),
                dbc.Col([
                    dbc.Button("Start Simulation", id="start-simulation-btn", color="primary", className="mt-4")
                ], width=3)
            ]),
            title="Simulation Settings"
        )
    ],
    flush=True,
    always_open=False,
    className="mb-3"
)

# Add a hidden div to display simulation status (if needed)
sim_status = html.Div(id="simulation-status", style={"display": "none"})

# Create header with controls
header = dbc.Row([
    dbc.Col([
        html.H3("Ship-Port Model Dashboard", className="mb-0")
    ], width=4),
    dbc.Col([
        html.Div([
            html.Span(f"Step: {global_stats['step']}", id="step-counter", className="me-3"),
            dbc.ButtonGroup([
                dbc.Button("Step", id="run-step-button", color="primary", size="sm", className="me-1"),
                dbc.Button("10 Steps", id="run-10-steps-button", color="secondary", size="sm", className="me-1"),
                dbc.Button("Reset", id="reset-button", color="danger", size="sm", className="me-1"),
            ], className="me-3"),
            dbc.Switch(
                id="auto-update-switch",
                label="Auto",
                value=False,
                className="d-inline-block"
            ),
            dcc.Interval(
                id='interval-component',
                interval=500,
                n_intervals=0,
                disabled=True
            )
        ], className="d-flex align-items-center")
    ], width=8, className="d-flex justify-content-end")
], className="mb-2 align-items-center")

# Create tabs for different views
tabs = dbc.Tabs([
    # Overview Tab
    dbc.Tab(label="Overview", children=[
        dbc.Row([
            # Key metrics cards
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Ships", className="card-title"),
                        html.H3(global_stats['ships']['total'], id="total-ships", className="card-text text-primary"),
                        html.P(f"Scrubbers: {global_stats['ships']['scrubber']}", id="scrubber-ships", className="card-text mb-0")
                    ])
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Environment", className="card-title"),
                        html.H3(global_stats['environment']['scrubber_trails'], id="scrubber-trails", className="card-text text-info"),
                    ])
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Economics", className="card-title"),
                        html.H3(f"${global_stats['economics']['total_revenue']:.0f}", id="total-revenue", className="card-text text-success"),
                        html.P(f"Avg Penalty: {global_stats['environment']['avg_penalty']:.2f}", id="avg-penalty", className="card-text mb-0")
                    ])
                ])
            ], width=3),
            
            # Main chart area with dropdown selector
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dcc.Dropdown(
                                    id='overview-chart-selector',
                                    options=[
                                        {'label': 'Ship Types', 'value': 'ship-types'},
                                        {'label': 'Port Revenue', 'value': 'port-revenue'},
                                        {'label': 'Port Occupancy', 'value': 'port-occupancy'},
                                        {'label': 'Ship Count Over Time', 'value': 'ship-time-series'},
                                        {'label': 'Environmental Metrics', 'value': 'env-time-series'}
                                    ],
                                    value='ship-types',
                                    clearable=False,
                                    className="mb-2"
                                )
                            ], width=6),
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button("Pie", id="chart-type-pie", size="sm", color="primary", outline=True, className="me-1"),
                                    dbc.Button("Bar", id="chart-type-bar", size="sm", color="primary", outline=False, className="me-1"),
                                    dbc.Button("Line", id="chart-type-line", size="sm", color="primary", outline=True)
                                ], id="chart-type-buttons", className="float-end")
                            ], width=6)
                        ]),
                        dcc.Graph(
                            id='overview-chart',
                            figure=px.pie(
                                ship_types_df, 
                                values='Count', 
                                names='Type', 
                                title='Ship Types Distribution',
                                height=300
                            ),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], width=9)
        ]),
        
        # Map and port table row
        dbc.Row([
            # Map
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Port Locations", className="card-title"),
                        dcc.Graph(
                            id='port-map',
                            figure=px.scatter_geo(
                                port_df,
                                lat='Latitude',
                                lon='Longitude',
                                hover_name='Port',
                                size='Maximum Capacity',
                                color='Allow Scrubber',
                                projection='natural earth',
                                height=300
                            ),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], width=6),
            
            # Port table
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Ports Overview", className="card-title"),
                        html.Div([
                            dbc.Table.from_dataframe(
                                port_df[['Port', 'Current Capacity', 'Maximum Capacity', 'Revenue', 'Allow Scrubber']], 
                                striped=True, 
                                bordered=False, 
                                hover=True,
                                size="sm",
                                id="port-table"
                            )
                        ], style={"maxHeight": "300px", "overflowY": "auto"})
                    ])
                ])
            ], width=6)
        ])
    ]),
    
    # Port Details Tab
    dbc.Tab(label="Port Details", children=[
        dbc.Row([
            # Port selector
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Select Port", className="card-title"),
                        dcc.Dropdown(
                            id='port-selector',
                            options=[{'label': data['name'], 'value': port_id} for port_id, data in port_data.items()],
                            value=list(port_data.keys())[0] if port_data else None,
                            clearable=False
                        ),
                        html.Hr(),
                        html.Div(id="selected-port-details")
                    ])
                ])
            ], width=3),
            
            # Port charts
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Tabs([
                            dbc.Tab(label="Ship Types", children=[
                                dcc.Graph(
                                    id='port-ship-types-chart',
                                    config={'displayModeBar': False},
                                    style={"height": "400px"}
                                )
                            ]),
                            dbc.Tab(label="Revenue", children=[
                                dcc.Graph(
                                    id='port-revenue-chart',
                                    config={'displayModeBar': False},
                                    style={"height": "400px"}
                                )
                            ]),
                            dbc.Tab(label="Occupancy", children=[
                                dcc.Graph(
                                    id='port-occupancy-chart',
                                    config={'displayModeBar': False},
                                    style={"height": "400px"}
                                )
                            ])
                        ])
                    ])
                ])
            ], width=9)
        ])
    ]),
    
    # Ship Statistics Tab
    dbc.Tab(label="Ship Statistics", children=[
        dbc.Row([
            # Ship type breakdown
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Ship Types", className="card-title"),
                        dcc.Graph(
                            id='ship-types-chart',
                            figure=px.pie(
                                ship_types_df, 
                                values='Count', 
                                names='Type', 
                                height=300
                            ),
                            config={'displayModeBar': False}
                        )
                    ])
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Scrubber Status", className="card-title"),
                        dcc.Graph(
                            id='scrubber-status-chart',
                            figure=px.bar(
                                scrubber_df, 
                                x='Status', 
                                y='Count', 
                                height=200
                            ),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], width=4),
            
            # Ship time series
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Ships Over Time", className="card-title"),
                        dcc.Dropdown(
                            id='ship-metric-selector',
                            options=[
                                {'label': 'Total Ships', 'value': 'Total Ships'},
                                {'label': 'Scrubber Ships', 'value': 'Scrubber Ships'},
                                {'label': 'Non-Scrubber Ships', 'value': 'Non-Scrubber Ships'},
                                {'label': 'All Ship Types', 'value': 'all'}
                            ],
                            value='all',
                            clearable=False,
                            className="mb-2"
                        ),
                        dcc.Graph(
                            id='ship-time-series-chart',
                            config={'displayModeBar': False},
                            style={"height": "500px"}
                        )
                    ])
                ])
            ], width=8)
        ])
    ]),
    
    # Environmental Tab
    dbc.Tab(label="Environmental", children=[
        dbc.Row([
            # Environmental metrics
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Current Metrics", className="card-title"),
                        dbc.ListGroup([
                            dbc.ListGroupItem([
                                html.Div("Scrubber Trails", className="fw-bold"),
                                html.Div(global_stats['environment']['scrubber_trails'], id="env-scrubber-trails")
                            ]),
                            dbc.ListGroupItem([
                                html.Div("Average Penalty", className="fw-bold"),
                                html.Div(f"{global_stats['environment']['avg_penalty']:.2f}", id="env-avg-penalty")
                            ])
                        ])
                    ])
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Port Scrubber Policies", className="card-title"),
                        dcc.Graph(
                            id='port-scrubber-policy-chart',
                            figure=px.pie(
                                port_df, 
                                names='Allow Scrubber', 
                                height=200,
                                color='Allow Scrubber',
                                color_discrete_map={'Yes': 'green', 'No': 'red'}
                            ),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], width=4),
            
            # Environmental time series
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Environmental Metrics Over Time", className="card-title"),
                        dcc.Dropdown(
                            id='env-metric-selector',
                            options=[
                                {'label': 'Scrubber Trails', 'value': 'Scrubber Trails'},
                                {'label': 'Average Penalty', 'value': 'Average Penalty'},
                                {'label': 'All Metrics', 'value': 'all'}
                            ],
                            value='all',
                            clearable=False,
                            className="mb-2"
                        ),
                        dcc.Graph(
                            id='env-time-series-chart',
                            config={'displayModeBar': False},
                            style={"height": "500px"}
                        )
                    ])
                ])
            ], width=8)
        ])
    ])
], className="mb-3")

# Layout - Set fixed height to prevent scrolling
app.layout = dbc.Container([
    simulation_settings,
    sim_status,
    header,
    tabs,
    dbc.Modal([
        dbc.ModalHeader("Port Details"),
        dbc.ModalBody(id="port-modal-body"),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-port-modal", className="ms-auto")
        ),
    ], id="port-detail-modal", size="lg"),
], fluid=True, className="p-3", style={"height": "100vh", "overflow": "hidden"})

# Add custom CSS to ensure no scrolling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                margin: 0;
                padding: 0;
                overflow: hidden;
            }
            .tab-content {
                height: calc(100vh - 120px);
                overflow: hidden;
            }
            .card {
                margin-bottom: 10px;
            }
            .card-body {
                padding: 10px;
            }
            .dash-table-container {
                max-height: 250px;
                overflow-y: auto;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Callbacks
@app.callback(
    Output('interval-component', 'disabled'),
    Input('auto-update-switch', 'value')
)
def toggle_auto_update(auto_update):
    return not auto_update

@app.callback(
    [Output('overview-chart', 'figure'),
     Output('chart-type-pie', 'outline'),
     Output('chart-type-bar', 'outline'),
     Output('chart-type-line', 'outline')],
    [Input('overview-chart-selector', 'value'),
     Input('chart-type-pie', 'n_clicks'),
     Input('chart-type-bar', 'n_clicks'),
     Input('chart-type-line', 'n_clicks'),
     Input('run-step-button', 'n_clicks'),
     Input('run-10-steps-button', 'n_clicks'),
     Input('reset-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')]
)
def update_overview_chart(chart_type, n_clicks_pie, n_clicks_bar, n_clicks_line, 
                         n_clicks_step, n_clicks_10, n_clicks_reset, n_intervals):
    ctx = dash.callback_context
    
    # Get updated data
    global_stats, port_data = collect_model_data()
    ship_types_df, scrubber_df, port_df, port_ship_types_df = create_dataframes(global_stats, port_data)
    global_ts_df, port_ts_df = create_time_series_dataframes()
    
    # Determine which button was clicked for chart type
    chart_style = 'pie'  # default
    pie_outline, bar_outline, line_outline = True, True, True
    
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if trigger_id == 'chart-type-pie':
            chart_style = 'pie'
            pie_outline, bar_outline, line_outline = False, True, True
        elif trigger_id == 'chart-type-bar':
            chart_style = 'bar'
            pie_outline, bar_outline, line_outline = True, False, True
        elif trigger_id == 'chart-type-line':
            chart_style = 'line'
            pie_outline, bar_outline, line_outline = True, True, False
    
    # Create the appropriate chart based on selection and style
    fig = go.Figure()
    height = 300
    
    if chart_type == 'ship-types':
        if chart_style == 'pie':
            fig = px.pie(ship_types_df, values='Count', names='Type', title='Ship Types Distribution', height=height)
        else:
            fig = px.bar(ship_types_df, x='Type', y='Count', title='Ship Types Distribution', height=height)
    
    elif chart_type == 'port-revenue':
        if chart_style == 'pie':
            fig = px.pie(port_df, values='Revenue', names='Port', title='Revenue by Port', height=height)
        else:
            fig = px.bar(port_df, x='Port', y='Revenue', title='Revenue by Port', height=height)
    
    elif chart_type == 'port-occupancy':
        if chart_style == 'pie':
            fig = px.pie(
                port_df, 
                values='Occupancy Rate', 
                names='Port', 
                title='Occupancy Rate by Port', 
                height=height
            )
        else:
            fig = px.bar(
                port_df, 
                x='Port', 
                y='Occupancy Rate', 
                title='Occupancy Rate by Port', 
                height=height
            )
    
    elif chart_type == 'ship-time-series':
        if not global_ts_df.empty:
            fig = px.line(
                global_ts_df, 
                x='Step', 
                y=['Total Ships', 'Scrubber Ships', 'Non-Scrubber Ships'], 
                title='Ship Count Over Time',
                height=height
            )
    
    elif chart_type == 'env-time-series':
        if not global_ts_df.empty:
            fig = px.line(
                global_ts_df, 
                x='Step', 
                y=['Scrubber Trails', 'Average Penalty'], 
                title='Environmental Metrics Over Time',
                height=height
            )
    
    # Update layout for better appearance
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig, pie_outline, bar_outline, line_outline

@app.callback(
    Output('selected-port-details', 'children'),
    [Input('port-selector', 'value'),
     Input('run-step-button', 'n_clicks'),
     Input('run-10-steps-button', 'n_clicks'),
     Input('reset-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')]
)
def update_port_details(port_id, n_clicks_step, n_clicks_10, n_clicks_reset, n_intervals):
    if not port_id:
        return html.P("No port selected")
    
    # Get updated data
    _, port_data = collect_model_data()
    
    if port_id not in port_data:
        return html.P("Port not found")
    
    port = port_data[port_id]
    
    return [
        html.H4(port['name'], className="mb-3"),
        dbc.ListGroup([
            dbc.ListGroupItem([
                html.Div("Capacity", className="fw-bold"),
                html.Div(f"{port['capacity']['current']}/{port['capacity']['maximum']}")
            ]),
            dbc.ListGroupItem([
                html.Div("Docked Ships", className="fw-bold"),
                html.Div(port['docked_ships']['total'])
            ]),
            dbc.ListGroupItem([
                html.Div("Revenue", className="fw-bold"),
                html.Div(f"${port['revenue']:.2f}")
            ]),
            dbc.ListGroupItem([
                html.Div("Scrubber Policy", className="fw-bold"),
                html.Div("Allow" if port['allow_scrubber'] else "Ban")
            ])
        ]),
        html.Div([
            dbc.Progress(
                value=port['capacity']['occupancy_rate'] * 100,
                label=f"{port['capacity']['occupancy_rate'] * 100:.1f}%",
                color="success" if port['capacity']['occupancy_rate'] < 0.7 else "warning" if port['capacity']['occupancy_rate'] < 0.9 else "danger",
                className="mt-3"
            )
        ])
    ]

@app.callback(
    [Output('port-ship-types-chart', 'figure'),
     Output('port-revenue-chart', 'figure'),
     Output('port-occupancy-chart', 'figure')],
    [Input('port-selector', 'value'),
     Input('run-step-button', 'n_clicks'),
     Input('run-10-steps-button', 'n_clicks'),
     Input('reset-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')]
)
def update_port_charts(port_id, n_clicks_step, n_clicks_10, n_clicks_reset, n_intervals):
    if not port_id:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No port selected")
        return empty_fig, empty_fig, empty_fig
    
    # Get updated data
    _, port_data = collect_model_data()
    _, port_ts_df = create_time_series_dataframes()
    
    if port_id not in port_data:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="Port not found")
        return empty_fig, empty_fig, empty_fig
    
    port = port_data[port_id]
    port_name = port['name']
    
    # Ship types chart
    docked_types = port['docked_ships']['by_type']
    if docked_types:
        ship_types_fig = px.pie(
            values=list(docked_types.values()),
            names=list(docked_types.keys()),
            title=f"Ship Types at {port_name}"
        )
    else:
        ship_types_fig = go.Figure()
        ship_types_fig.update_layout(title=f"No ships docked at {port_name}")
    
    # Revenue chart
    port_revenue_data = port_ts_df[port_ts_df['Port'] == port_name] if not port_ts_df.empty else pd.DataFrame()
    if not port_revenue_data.empty:
        revenue_fig = px.line(
            port_revenue_data,
            x='Step',
            y='Revenue',
            title=f"{port_name} Revenue Over Time"
        )
    else:
        revenue_fig = go.Figure()
        revenue_fig.update_layout(title=f"No revenue data for {port_name}")
    
    # Occupancy chart
    if not port_revenue_data.empty:
        occupancy_fig = px.line(
            port_revenue_data,
            x='Step',
            y='Occupancy Rate',
            title=f"{port_name} Occupancy Rate Over Time"
        )
    else:
        occupancy_fig = go.Figure()
        occupancy_fig.update_layout(title=f"No occupancy data for {port_name}")
    
    # Update layout for better appearance
    for fig in [ship_types_fig, revenue_fig, occupancy_fig]:
        fig.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
    
    return ship_types_fig, revenue_fig, occupancy_fig

@app.callback(
    Output('ship-time-series-chart', 'figure'),
    [Input('ship-metric-selector', 'value'),
     Input('run-step-button', 'n_clicks'),
     Input('run-10-steps-button', 'n_clicks'),
     Input('reset-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')]
)
def update_ship_time_series(metric, n_clicks_step, n_clicks_10, n_clicks_reset, n_intervals):
    # Get updated data
    global_ts_df, _ = create_time_series_dataframes()
    
    if global_ts_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No time series data available")
        return fig
    
    if metric == 'all':
        y_cols = ['Total Ships', 'Scrubber Ships', 'Non-Scrubber Ships']
    else:
        y_cols = [metric]
    
    fig = px.line(
        global_ts_df,
        x='Step',
        y=y_cols,
        title='Ship Count Over Time'
    )
    
    # Update layout for better appearance
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

@app.callback(
    Output('env-time-series-chart', 'figure'),
    [Input('env-metric-selector', 'value'),
     Input('run-step-button', 'n_clicks'),
     Input('run-10-steps-button', 'n_clicks'),
     Input('reset-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')]
)
def update_env_time_series(metric, n_clicks_step, n_clicks_10, n_clicks_reset, n_intervals):
    # Get updated data
    global_ts_df, _ = create_time_series_dataframes()
    
    if global_ts_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No time series data available")
        return fig
    
    if metric == 'all':
        y_cols = ['Scrubber Trails', 'Average Penalty']
    else:
        y_cols = [metric]
    
    fig = px.line(
        global_ts_df,
        x='Step',
        y=y_cols,
        title='Environmental Metrics Over Time'
    )
    
    # Update layout for better appearance
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

@app.callback(
    [
        Output('step-counter', 'children'),
        Output('total-ships', 'children'),
        Output('scrubber-ships', 'children'),
        Output('scrubber-trails', 'children'),
        Output('avg-penalty', 'children'),
        Output('total-revenue', 'children'),
        Output('ship-types-chart', 'figure'),
        Output('scrubber-status-chart', 'figure'),
        Output('port-map', 'figure'),
        Output('port-table', 'children'),
        Output('port-scrubber-policy-chart', 'figure'),
        Output('env-scrubber-trails', 'children'),
        Output('env-avg-penalty', 'children')
    ],
    [
        Input('run-step-button', 'n_clicks'),
        Input('run-10-steps-button', 'n_clicks'),
        Input('reset-button', 'n_clicks'),
        Input('interval-component', 'n_intervals')
    ],
    prevent_initial_call=True
)
def update_dashboard(n_clicks_step, n_clicks_10, n_clicks_reset, n_intervals):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'reset-button':
        global model, historical_data
        model = ShipPortModel(width=100, height=100, num_ships=300)
        
        # Reset historical data
        historical_data = {
            'steps': [],
            'global': {
                'total_ships': [],
                'scrubber_ships': [],
                'non_scrubber_ships': [],
                'scrubber_trails': [],
                'avg_penalty': [],
                'total_revenue': []
            },
            'ports': defaultdict(lambda: {
                'revenue': [],
                'occupancy': [],
                'docked_ships': []
            })
        }
        
        for _ in range(10):
            model.step()
    else:
        # Only step the model if the current step is less than 300:
        if model.schedule.steps < 300:
            if trigger_id == 'run-step-button':
                model.step()
            elif trigger_id == 'run-10-steps-button':
                for _ in range(10):
                    if model.schedule.steps < 300:
                        model.step()
                    else:
                        break
            elif trigger_id == 'interval-component':
                model.step()
    
    # Collect updated data
    global_stats, port_data = collect_model_data()
    ship_types_df, scrubber_df, port_df, port_ship_types_df = create_dataframes(global_stats, port_data)
    
    # Update all outputs
    step_counter = f"Step: {global_stats['step']}"
    total_ships = global_stats['ships']['total']
    scrubber_ships = f"Scrubbers: {global_stats['ships']['scrubber']}"
    scrubber_trails = global_stats['environment']['scrubber_trails']
    avg_penalty = f"Avg Penalty: {global_stats['environment']['avg_penalty']:.2f}"
    total_revenue = f"${global_stats['economics']['total_revenue']:.0f}"
    
    ship_types_pie = px.pie(
        ship_types_df, 
        values='Count', 
        names='Type', 
        height=300
    )
    
    scrubber_status_bar = px.bar(
        scrubber_df, 
        x='Status', 
        y='Count', 
        height=200
    )
    
    port_map = px.scatter_geo(
        port_df,
        lat='Latitude',
        lon='Longitude',
        hover_name='Port',
        size='Maximum Capacity',
        color='Allow Scrubber',
        projection='natural earth',
        height=300
    )
    port_map.update_geos(
        center=dict(lat=56, lon=2),          # Center roughly over the North Sea
        projection_scale=2,                   # Adjust scale for appropriate zoom
        lataxis_range=[50, 64],               # Set latitude bounds
        lonaxis_range=[-8, 12]                 # Set longitude bounds
    )
    
    port_table_children = dbc.Table.from_dataframe(
        port_df[['Port', 'Current Capacity', 'Maximum Capacity', 'Revenue', 'Allow Scrubber']], 
        striped=True, 
        bordered=False, 
        hover=True,
        size="sm"
    ).children
    
    port_scrubber_policy_chart = px.pie(
        port_df, 
        names='Allow Scrubber', 
        height=200,
        color='Allow Scrubber',
        color_discrete_map={'Yes': 'green', 'No': 'red'}
    )
    
    env_scrubber_trails = global_stats['environment']['scrubber_trails']
    env_avg_penalty = f"{global_stats['environment']['avg_penalty']:.2f}"
    
    # Update layout for better appearance
    for fig in [ship_types_pie, scrubber_status_bar, port_map, port_scrubber_policy_chart]:
        fig.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
    
    return [
        step_counter,
        total_ships,
        scrubber_ships,
        scrubber_trails,
        avg_penalty,
        total_revenue,
        ship_types_pie,
        scrubber_status_bar,
        port_map,
        port_table_children,
        port_scrubber_policy_chart,
        env_scrubber_trails,
        env_avg_penalty
    ]
@app.callback(
    Output('simulation-status', 'children'),
    Input('start-simulation-btn', 'n_clicks'),
    State('sim-width', 'value'),
    State('sim-height', 'value'),
    State('sim-num-ships', 'value')
)
def start_simulation(n_clicks, width, height, num_ships):
    if not n_clicks:
        return ""
    global model, historical_data
    model = ShipPortModel(width=int(width), height=int(height), num_ships=int(num_ships))
    # Reset historical data
    historical_data = {
        'steps': [],
        'global': {
            'total_ships': [],
            'scrubber_ships': [],
            'non_scrubber_ships': [],
            'scrubber_trails': [],
            'avg_penalty': [],
            'total_revenue': []
        },
        'ports': defaultdict(lambda: {
            'revenue': [],
            'occupancy': [],
            'docked_ships': []
        })
    }
    for _ in range(10):
        model.step()
    return f"Simulation started with width={width}, height={height}, and num_ships={num_ships}"
# Run the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8051)
