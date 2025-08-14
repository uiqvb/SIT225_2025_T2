import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px

# Load data
df = pd.read_csv("gyro_data_20250812_153117.csv")

# Create app
app = Dash(__name__)

# Layout
app.layout = html.Div([
    html.H1("Gyroscope Data Dashboard"),

    html.Div([
        html.Label("Select Graph Type:"),
        dcc.Dropdown(
            id='graph-type',
            options=[
                {'label': 'Line Graph', 'value': 'line'},
                {'label': 'Scatter Plot', 'value': 'scatter'},
                {'label': 'Histogram', 'value': 'histogram'}
            ],
            value='line',
            clearable=False,
            style={'width': '200px'}
        ),
    ]),

    html.Div([
        html.Label("Select Axes:"),
        dcc.Checklist(
            id='axis-select',
            options=[
                {'label': 'X', 'value': 'gyro_x'},
                {'label': 'Y', 'value': 'gyro_y'},
                {'label': 'Z', 'value': 'gyro_z'}
            ],
            value=['gyro_x', 'gyro_y', 'gyro_z'],
            inline=True
        ),
    ]),

    html.Div([
        html.Label("Number of samples to display:"),
        dcc.Input(
            id='sample-count',
            type='number',
            value=200,
            min=10,
            step=10
        ),
        html.Button("Previous", id='prev-btn', n_clicks=0),
        html.Button("Next", id='next-btn', n_clicks=0)
    ], style={'margin-top': '10px'}),

    dcc.Graph(id='gyro-graph'),

    html.Div(id='data-summary', style={'margin-top': '20px'})
])

@app.callback(
    [Output('gyro-graph', 'figure'),
     Output('data-summary', 'children')],
    [Input('graph-type', 'value'),
     Input('axis-select', 'value'),
     Input('sample-count', 'value'),
     Input('prev-btn', 'n_clicks'),
     Input('next-btn', 'n_clicks')]
)
def update_graph(graph_type, selected_axes, sample_count, prev_clicks, next_clicks):
    page = next_clicks - prev_clicks
    start = page * sample_count
    end = start + sample_count
    dff = df.iloc[start:end]

    if graph_type == 'line':
        fig = px.line(dff, y=selected_axes, title="Gyroscope Line Chart")
    elif graph_type == 'scatter':
        fig = px.scatter(dff, y=selected_axes, title="Gyroscope Scatter Plot")
    elif graph_type == 'histogram':
        fig = px.histogram(dff, x=selected_axes[0], title="Gyroscope Histogram")

    summary_table = dff[selected_axes].describe().reset_index()
    summary_html = html.Table([
        html.Thead(html.Tr([html.Th(col) for col in summary_table.columns])),
        html.Tbody([
            html.Tr([
                html.Td(summary_table.iloc[i][col]) for col in summary_table.columns
            ]) for i in range(len(summary_table))
        ])
    ])

    return fig, html.Div([html.H4("Data Summary"), summary_html])

if __name__ == '__main__':

    # new
    app.run(debug=True)

