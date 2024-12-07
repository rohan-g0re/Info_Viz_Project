import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Load and preprocess the data
def load_and_preprocess_data():
    main_df = pd.read_csv('flights.csv', low_memory=False)
    airport_df = pd.read_csv("airports.csv")
    main_df['Date'] = pd.to_datetime(main_df[['YEAR', 'MONTH', 'DAY']])
    main_df = main_df.sort_values(by=['Date'])
    origin_df = airport_df.rename(columns={
        'IATA_CODE': 'ORIGIN_IATA_CODE',
        'LATITUDE': 'origin_lat',
        'LONGITUDE': 'origin_long',
        'STATE': 'origin_state'
    })[['ORIGIN_IATA_CODE', 'origin_lat', 'origin_long', 'origin_state']]

    dest_df = airport_df.rename(columns={
        'IATA_CODE': 'DEST_IATA_CODE',
        'LATITUDE': 'dest_lat',
        'LONGITUDE': 'dest_long'
    })[['DEST_IATA_CODE', 'dest_lat', 'dest_long']]

    main_df = main_df.merge(origin_df, left_on='ORIGIN_AIRPORT', right_on='ORIGIN_IATA_CODE', how='left')
    main_df = main_df.merge(dest_df, left_on='DESTINATION_AIRPORT', right_on='DEST_IATA_CODE', how='left')

    main_df.fillna(0, inplace=True)
    
    return main_df

main_df = load_and_preprocess_data()

# Get the unique states and airports for dropdowns
states = main_df['origin_state'].unique()
airports_by_state = main_df.groupby('origin_state')['ORIGIN_AIRPORT'].unique().to_dict()
airport_coords = main_df[['ORIGIN_AIRPORT', 'origin_lat', 'origin_long']].drop_duplicates()

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Flight Dashboard"

app.layout = html.Div([
    dcc.Tabs([

        dcc.Tab(label='Airport Staff', children=[
            # Global time slicer
            html.Div([
                dcc.DatePickerRange(
                    id='time-slicer',
                    start_date=main_df['Date'].min(),
                    end_date=main_df['Date'].max(),
                    display_format='YYYY-MM-DD',
                    style={'marginBottom': '20px'}
                )
            ]),

            html.Div([
                html.Div([
                    # Dropdowns for state and airport
                    html.Label("Select State:"),
                    
                    dcc.Dropdown(
                        id='state-dropdown',
                        options=[{'label': state, 'value': state} for state in states],
                        placeholder="Select a state"
                    ),
                    
                    html.Label("Select Airport:"),
                    
                    dcc.Dropdown(
                        id='airport-dropdown',
                        placeholder="Select an airport"
                    )
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                
                
                html.Div([
                    # Map placeholder
                    dcc.Graph(id='airport-map')
                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
            ]),



            html.Div([
                # Line chart for taxi delays
                dcc.Graph(id='taxi-delay-line-chart')
            ], style={'width': '100%', 'marginTop': '20px'}),
            
            
            
            html.Div([
                # Two pie charts
                html.Div([
                    dcc.Graph(id='delay-distribution-pie-chart'),
                ], style={'width': '48%', 'display': 'inline-block'}),
                html.Div([
                    dcc.Graph(id='time-split-pie-chart'),
                ], style={'width': '48%', 'display': 'inline-block'})
            ], style={'marginTop': '20px'}),
            
            
            
            html.Div([
                # Map for top connected airports
                html.Label("Select Flight Direction:"),
                
                dcc.RadioItems(
                    id='flight-direction-radio',
                    options=[
                        {'label': 'Incoming Flights', 'value': 'incoming'},
                        {'label': 'Outgoing Flights', 'value': 'outgoing'}
                    ],
                    value='incoming',
                    inline=True
                ),
                
                
                dcc.Graph(id='connected-airports-map')


            ], style={'marginTop': '20px'})
        ]),
        
        
        
        
        dcc.Tab(label='Airline Company', children=[
            html.Div("Content for Airline Company will go here.")
        ]),
        
        
        
        dcc.Tab(label='Passenger', children=[
            html.Div("Content for Passenger will go here.")
        ])
    ])
])

@app.callback(
    Output('airport-dropdown', 'options'),
    Input('state-dropdown', 'value')
)
def update_airport_dropdown(selected_state):
    if not selected_state:
        return []
    return [{'label': airport, 'value': airport} for airport in airports_by_state[selected_state]]

@app.callback(
    
    [Output('taxi-delay-line-chart', 'figure'),
     Output('airport-map', 'figure'),
     Output('delay-distribution-pie-chart', 'figure'),
     Output('time-split-pie-chart', 'figure')],

    [Input('state-dropdown', 'value'),
     Input('airport-dropdown', 'value'),
     Input('time-slicer', 'start_date'),
     Input('time-slicer', 'end_date')]
)
def update_charts(selected_state, selected_airport, start_date, end_date):
    if not selected_state or not selected_airport or not start_date or not end_date:
        return {}, {}, {}, {}

    # Filter dataset based on selected airport and time frame
    filtered_df = main_df[(main_df['ORIGIN_AIRPORT'] == selected_airport) &
                          (main_df['Date'] >= start_date) &
                          (main_df['Date'] <= end_date)]

    # Taxi delays line chart
    daily_delays = filtered_df.groupby('Date').agg(
        avg_taxi_in=('TAXI_IN', 'mean'),
        avg_taxi_out=('TAXI_OUT', 'mean')
    ).reset_index()

    taxi_fig = px.line(
        daily_delays, x='Date', y=['avg_taxi_in', 'avg_taxi_out'],
        labels={'Date': 'Date', 'value': 'Delay (minutes)', 'variable': 'Taxi Type'},
        title=f"Average Daily Taxi Delays at {selected_airport}"
    )

    # Airport location map
    airport_info = airport_coords[airport_coords['ORIGIN_AIRPORT'] == selected_airport]
    map_fig = px.scatter_geo(
        airport_info,
        lat='origin_lat',
        lon='origin_long',
        text='ORIGIN_AIRPORT',
        title=f"Location of {selected_airport}"
    )

    # Delay Distribution Pie Chart
    delay_totals = {
        'Air System': filtered_df['AIR_SYSTEM_DELAY'].sum(),
        'Security': filtered_df['SECURITY_DELAY'].sum(),
        'Airline': filtered_df['AIRLINE_DELAY'].sum(),
        'Late Aircraft': filtered_df['LATE_AIRCRAFT_DELAY'].sum(),
        'Weather': filtered_df['WEATHER_DELAY'].sum(),
        'Miscellaneous': max(0, filtered_df['ARRIVAL_DELAY'].sum() -
                             (filtered_df['AIR_SYSTEM_DELAY'].sum() +
                              filtered_df['SECURITY_DELAY'].sum() +
                              filtered_df['AIRLINE_DELAY'].sum() +
                              filtered_df['LATE_AIRCRAFT_DELAY'].sum() +
                              filtered_df['WEATHER_DELAY'].sum()))
    }
    delay_fig = px.pie(
        names=list(delay_totals.keys()),
        values=list(delay_totals.values()),
        title="Delay Distribution"
    )

    # Time Split Pie Chart
    time_totals = {
        'Departure Delay': filtered_df['DEPARTURE_DELAY'].sum(),
        'Arrival Delay': filtered_df['ARRIVAL_DELAY'].sum(),
        'Taxi In': filtered_df['TAXI_IN'].sum(),
        'Taxi Out': filtered_df['TAXI_OUT'].sum()
    }
    time_fig = px.pie(
        names=list(time_totals.keys()),
        values=list(time_totals.values()),
        title="Time Split"
    )

    return taxi_fig, map_fig, delay_fig, time_fig


@app.callback(
    Output('connected-airports-map', 'figure'),
    [Input('airport-dropdown', 'value'),
     Input('time-slicer', 'start_date'),
     Input('time-slicer', 'end_date'),
     Input('flight-direction-radio', 'value')]
)
def update_connected_airports_map(selected_airport, start_date, end_date, flight_direction):
    if not selected_airport or not start_date or not end_date or not flight_direction:
        return {}

    # Filter dataset based on time frame
    filtered_df = main_df[(main_df['Date'] >= start_date) & (main_df['Date'] <= end_date)]

    if flight_direction == 'incoming':
        # Get incoming flights to the selected airport
        connected_df = filtered_df[filtered_df['DESTINATION_AIRPORT'] == selected_airport]
        top_airports = connected_df['ORIGIN_AIRPORT'].value_counts().head(7).index
        top_df = connected_df[connected_df['ORIGIN_AIRPORT'].isin(top_airports)]
        lat_col, lon_col = 'origin_lat', 'origin_long'
        airport_column = 'ORIGIN_AIRPORT'
    else:
        # Get outgoing flights from the selected airport
        connected_df = filtered_df[filtered_df['ORIGIN_AIRPORT'] == selected_airport]
        top_airports = connected_df['DESTINATION_AIRPORT'].value_counts().head(7).index
        top_df = connected_df[connected_df['DESTINATION_AIRPORT'].isin(top_airports)]
        lat_col, lon_col = 'dest_lat', 'dest_long'
        airport_column = 'DESTINATION_AIRPORT'

    # Ensure the filtered dataset only includes the relevant rows
    top_df = top_df.groupby(airport_column).first().reset_index()

    # Create the map
    map_fig = px.scatter_geo(
        top_df,
        lat=lat_col,
        lon=lon_col,
        text=airport_column,
        title=f"Top 7 Connected Airports ({flight_direction.capitalize()} Flights)",
        size=top_df.groupby(airport_column).size(),
    )

    return map_fig


# @app.callback(
#     Output('airline-kepler-map', 'data'),
#     [Input('airline-time-slicer', 'start_date'),
#      Input('airline-time-slicer', 'end_date'),
#      Input('airline-visualization-dropdown', 'value')]
# )
# def update_kepler_map(start_date, end_date, selected_chart):
#     if not start_date or not end_date or not selected_chart:
#         return {}

#     # Filter the data based on the selected timeframe
#     filtered_df = main_df[(main_df['Date'] >= start_date) & (main_df['Date'] <= end_date)]

#     if selected_chart == 'popular-routes':
#         # Calculate total flights handled (incoming + outgoing)
#         incoming_flights = filtered_df.groupby('DESTINATION_AIRPORT').size().reset_index(name='incoming_flights')
#         outgoing_flights = filtered_df.groupby('ORIGIN_AIRPORT').size().reset_index(name='outgoing_flights')

#         flights_handled = pd.merge(
#             incoming_flights, outgoing_flights,
#             left_on='DESTINATION_AIRPORT',
#             right_on='ORIGIN_AIRPORT',
#             how='outer'
#         ).fillna(0)
#         flights_handled['total_flights_handled'] = flights_handled['incoming_flights'] + flights_handled['outgoing_flights']
#         flights_handled = flights_handled.sort_values('total_flights_handled', ascending=False).head(20)

#         # Merge with airport coordinates
#         flights_handled = flights_handled.merge(airport_coords, left_on='DESTINATION_AIRPORT', right_on='ORIGIN_AIRPORT', how='left')

#         # Prepare data for Kepler.gl
#         kepler_data = flights_handled[['origin_lat', 'origin_long', 'total_flights_handled']]
#         kepler_data.rename(columns={'origin_lat': 'latitude', 'origin_long': 'longitude'}, inplace=True)

#         # Convert data to JSON for Kepler.gl
#         kepler_json = json.loads(kepler_data.to_json(orient='records'))

#         # Create Kepler.gl configuration
#         config = {
#             "version": "v1",
#             "config": {
#                 "visState": {
#                     "filters": [],
#                     "layers": [
#                         {
#                             "id": "hotspot-layer",
#                             "type": "heatmap",
#                             "config": {
#                                 "dataId": "hotspots",
#                                 "label": "Flight Hotspots",
#                                 "color": [255, 0, 0],
#                                 "columns": {
#                                     "lat": "latitude",
#                                     "lng": "longitude",
#                                 },
#                                 "isVisible": True,
#                             }
#                         }
#                     ],
#                     "interactionConfig": {
#                         "tooltip": {"fieldsToShow": {"hotspots": ["latitude", "longitude", "total_flights_handled"]}}
#                     },
#                     "layerBlending": "normal"
#                 },
#                 "mapState": {
#                     "bearing": 0,
#                     "pitch": 0,
#                     "latitude": kepler_data['latitude'].mean(),
#                     "longitude": kepler_data['longitude'].mean(),
#                     "zoom": 4
#                 },
#                 "mapStyle": {"styleType": "dark"}
#             }
#         }

#         # Return data and configuration for Kepler.gl
#         return {"data": kepler_json, "config": config}

#     return {}


if __name__ == "__main__":
    app.run_server(debug=True)
