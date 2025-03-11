import asyncio
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import threading

from generated.status.PiStatus_pb2 import PiStatus
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address

# Store timestamps along with stats
time_series = []
stats_history = {}

# Create the dashboard app
app = Dash(__name__)
app.layout = html.Div([
    dcc.Graph(id='live-graph'),
    dcc.Interval(
        id='interval-component',
        interval=1000,  # update every second
        n_intervals=0
    )
])

@app.callback(
    Output('live-graph', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_graph(_):
    fig = make_subplots(rows=3, cols=1, 
                        subplot_titles=('CPU Usage', 'Memory Usage', 'Network Usage'))
    
    for pi_name in stats_history:
        pi_data = stats_history[pi_name]
        
        # CPU plot
        fig.add_trace(
            go.Scatter(x=time_series, y=pi_data['cpu'], name=f'{pi_name} CPU'),
            row=1, col=1
        )
        
        # Memory plot
        fig.add_trace(
            go.Scatter(x=time_series, y=pi_data['memory'], name=f'{pi_name} Memory'),
            row=2, col=1
        )
        
        # Network plot
        fig.add_trace(
            go.Scatter(x=time_series, y=pi_data['net_in'], name=f'{pi_name} Net In'),
            row=3, col=1
        )
    
    fig.update_layout(height=900)
    return fig

async def main():
    pi_stats_dict: dict[str, PiStatus] = {}
    
    autobahn_server = Autobahn(Address("10.47.65.7", 8080))
    await autobahn_server.begin()
    
    async def stats_sub(bytes_in: bytes):
        nonlocal pi_stats_dict
        bytes_status = PiStatus.FromString(bytes_in)
        pi_stats_dict[bytes_status.pi_name] = bytes_status
        
        # Update time series data
        current_time = datetime.now()
        time_series.append(current_time)
        
        # Keep only last 100 points
        if len(time_series) > 100:
            time_series.pop(0)
        
        # Update stats history
        if bytes_status.pi_name not in stats_history:
            stats_history[bytes_status.pi_name] = {
                'cpu': [],
                'memory': [],
                'net_in': []
            }
            
        stats = stats_history[bytes_status.pi_name]
        stats['cpu'].append(bytes_status.cpu_usage_total)
        stats['memory'].append(bytes_status.memory_usage)
        stats['net_in'].append(bytes_status.net_usage_in)
        
        # Trim history to match time series
        if len(stats['cpu']) > 100:
            for key in stats:
                stats[key].pop(0)
    
    await autobahn_server.subscribe("stats/publish", stats_sub)

if __name__ == "__main__":
    # Run the Dash app in a separate thread
    threading.Thread(target=app.run_server, daemon=True).start()
    
    # Run the main asyncio loop
    asyncio.run(main())