import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import keplergl
from keplergl import KeplerGl

# # BETTER

# def load_and_preprocess_data():
#     main_df = pd.read_csv('flights.csv', low_memory=False)
#     airport_df = pd.read_csv("airports.csv")
#     airline_df = pd.read_csv("airlines.csv").iloc[:, :2].rename(columns={
#         'IATA_CODE': 'AIRLINE_CODE', 
#         'AIRLINE': 'AIRLINE_NAME'
#     })


#     # Step 1: Merging airport information
#     # For origin airport
#     main_df = main_df.merge(airport_df, left_on='ORIGIN_AIRPORT', right_on='IATA_CODE', how='left')
#     main_df = main_df.rename(columns={
#         'AIRPORT': 'origin_AIRPORT',
#         'CITY': 'origin_CITY',
#         'STATE': 'origin_STATE',
#         'LATITUDE': 'origin_LATITUDE',
#         'LONGITUDE': 'origin_LONGITUDE'
#     })

#     # For destination airport
#     main_df = main_df.merge(airport_df, left_on='DESTINATION_AIRPORT', right_on='IATA_CODE', how='left', suffixes=('', '_dest'))
#     main_df = main_df.rename(columns={
#         'AIRPORT': 'dest_AIRPORT',
#         'CITY': 'dest_CITY',
#         'STATE': 'dest_STATE',
#         'LATITUDE': 'dest_LATITUDE',
#         'LONGITUDE': 'dest_LONGITUDE'
#     })

#     # Remove duplicate columns
#     main_df = main_df.drop(['IATA_CODE', 'IATA_CODE_dest', 'COUNTRY', 'COUNTRY_dest'], axis=1)

#     # Step 2: Merging airline information
#     main_df = main_df.merge(airline_df, left_on='AIRLINE', right_on='AIRLINE_CODE', how='left')
#     main_df = main_df.rename(columns={'AIRLINE_NAME': 'AIRLINE_NAME'})

#     # Remove duplicate column
#     main_df = main_df.drop('AIRLINE_CODE', axis=1)

#     main_df.fillna({ 'dest_LATITUDE': 0.0}, inplace=True)
#     main_df.fillna(0, inplace=True)
#     main_df = main_df[main_df['dest_LATITUDE'] != 0.0]

#     return main_df, airport_df, airline_df




def load_and_preprocess_data():
    # Load main data
    main_df = pd.read_csv('flights.csv', low_memory=False)
    airport_df = pd.read_csv("airports.csv")
    airline_df = pd.read_csv("airlines.csv").iloc[:, :2].rename(columns={
        'IATA_CODE': 'AIRLINE_CODE', 
        'AIRLINE': 'AIRLINE_NAME'
    })

    # Add a date column for filtering
    main_df['Date'] = pd.to_datetime(main_df[['YEAR', 'MONTH', 'DAY']])
    main_df = main_df.sort_values(by=['Date'])

    # Merge airlines to include full airline names
    main_df = main_df.merge(airline_df, left_on='AIRLINE', right_on='AIRLINE_CODE', how='left')

    # Merge with airport data for additional details if needed
    origin_df = airport_df.rename(columns={
        'IATA_CODE': 'ORIGIN_IATA_CODE',
        'LATITUDE': 'origin_lat',
        'LONGITUDE': 'origin_long',
        'STATE': 'origin_state'
    })[['ORIGIN_IATA_CODE', 'origin_lat', 'origin_long', 'origin_state']]

    main_df = main_df.merge(origin_df, left_on='ORIGIN_AIRPORT', right_on='ORIGIN_IATA_CODE', how='left')

    # Replace NaN with 0 or empty strings to prevent issues
    main_df.fillna({'AIRLINE_NAME': 'Unknown Airline'}, inplace=True)
    main_df.fillna(0, inplace=True)

    return main_df, airport_df, airline_df


main_df, airport_df, airline_df = load_and_preprocess_data()

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
        
        # Airline Tab
        dcc.Tab(label='Airline Company', children=[
            html.Div([
                html.Label("Select Timeframe:"),
                dcc.DatePickerRange(
                    id='airline-time-slicer',
                    start_date=main_df['Date'].min(),
                    end_date=main_df['Date'].max(),
                    display_format='YYYY-MM-DD'
                ),
                html.Label("Select Visualization:"),
                dcc.Dropdown(
                    id='airline-visualization-dropdown',
                    options=[
                        {'label': 'Popular Routes on Map', 'value': 'popular-routes'}
                    ],
                    placeholder="Select a visualization"
                ),
                html.Div([
                    dcc.Graph(id='geo-routes-map')  # Replace iframe with Graph
                ])
            ])
        ]),

        dcc.Tab(label='Passenger', children=[
            # Time slicer
            html.Div([
                html.Label("Select Timeframe:"),
                dcc.DatePickerRange(
                    id='passenger-time-slicer',
                    start_date=main_df['Date'].min(),
                    end_date=main_df['Date'].max(),
                    display_format='YYYY-MM-DD',
                    style={'marginBottom': '20px'}
                ),
            ]),
            
            # Dropdown for selecting chart type
            html.Div([
                html.Label("Select Category:"),
                dcc.Dropdown(
                    id='passenger-bar-chart-dropdown',
                    options=[
                        {'label': 'Top 10 Airlines with Least Delay', 'value': 'least_delay'},
                        {'label': 'Top 10 Airlines with Highest Delay', 'value': 'highest_delay'},
                        {'label': 'Top 10 Airlines with Most Cancelled Flights', 'value': 'most_cancelled'},
                        {'label': 'Top 10 Airlines with Most Diverted Flights', 'value': 'most_diverted'}
                    ],
                    placeholder="Select a category"
                )
            ], style={'marginTop': '20px'}),

            # Bar chart
            html.Div([
                dcc.Graph(id='passenger-bar-chart')
            ], style={'marginTop': '20px'})
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




import geopandas as gpd
import plotly.express as px
from shapely.geometry import LineString

@app.callback(
    Output('geo-routes-map', 'figure'),
    [Input('airline-time-slicer', 'start_date'),
     Input('airline-time-slicer', 'end_date'),
     Input('airline-visualization-dropdown', 'value')]
)
def update_geopandas_map(start_date, end_date, selected_chart):
    if not start_date or not end_date or not selected_chart:
        return {}

    # Filter the data based on the selected timeframe
    filtered_df = main_df[(main_df['Date'] >= start_date) & (main_df['Date'] <= end_date)]

    if selected_chart == 'popular-routes':
        # Calculate total flights handled (incoming + outgoing)
        route_df = filtered_df.groupby(['ORIGIN_AIRPORT', 'DESTINATION_AIRPORT']).size().reset_index(name='flight_count')

        # Merge with airport coordinates
        origin_coords = airport_df.rename(columns={'IATA_CODE': 'ORIGIN_AIRPORT'})
        dest_coords = airport_df.rename(columns={'IATA_CODE': 'DESTINATION_AIRPORT'})
        route_df = route_df.merge(origin_coords[['ORIGIN_AIRPORT', 'LATITUDE', 'LONGITUDE']],
                                  on='ORIGIN_AIRPORT', how='left')
        route_df = route_df.merge(dest_coords[['DESTINATION_AIRPORT', 'LATITUDE', 'LONGITUDE']],
                                  on='DESTINATION_AIRPORT', how='left')

        # Validate route_df
        if route_df.empty:
            return px.scatter_geo(title="No Routes Available")

        # Create the map using scatter_geo for lines
        fig = go.Figure()

        for _, row in route_df.iterrows():
            fig.add_trace(
                go.Scattergeo(
                    locationmode='USA-states',
                    lon=[row['LONGITUDE_x'], row['LONGITUDE_y']],
                    lat=[row['LATITUDE_x'], row['LATITUDE_y']],
                    mode='lines',
                    line=dict(width=2, color='blue'),
                    hoverinfo='text',
                    text=f"Route: {row['ORIGIN_AIRPORT']} → {row['DESTINATION_AIRPORT']} ({row['flight_count']} flights)"
                )
            )

        # Add place markers for airports
        fig.add_trace(
            go.Scattergeo(
                locationmode='USA-states',
                lon=route_df['LONGITUDE_x'],
                lat=route_df['LATITUDE_x'],
                mode='markers',
                marker=dict(size=8, symbol='circle'),
                text=route_df['ORIGIN_AIRPORT'],
                hoverinfo='text'
            )
        )
        fig.add_trace(
            go.Scattergeo(
                locationmode='USA-states',
                lon=route_df['LONGITUDE_y'],
                lat=route_df['LATITUDE_y'],
                mode='markers',
                marker=dict(size=8, symbol='circle'),
                text=route_df['DESTINATION_AIRPORT'],
                hoverinfo='text'
            )
        )

        # Update map layout
        fig.update_layout(
            title="Popular Routes",
            geo=dict(
                scope='usa',
                projection=go.layout.geo.Projection(type='albers usa'),
                showland=True,
                landcolor='rgb(243, 243, 243)',
                subunitwidth=1,
                countrywidth=1,
                subunitcolor="rgb(217, 217, 217)",
                countrycolor="rgb(217, 217, 217)"
            )
        )

        return fig

    return {}



@app.callback(
    Output('passenger-bar-chart', 'figure'),
    [Input('passenger-time-slicer', 'start_date'),
     Input('passenger-time-slicer', 'end_date'),
     Input('passenger-bar-chart-dropdown', 'value')]
)
def update_passenger_bar_chart(start_date, end_date, selected_category):
    if not start_date or not end_date or not selected_category:
        return {}

    # Filter data by selected timeframe
    filtered_df = main_df[(main_df['Date'] >= start_date) & (main_df['Date'] <= end_date)]

    # Initialize variables
    x = []
    y = []
    title = ""

    if selected_category in ['least_delay', 'highest_delay']:
        # Calculate total delays
        filtered_df['TOTAL_DELAY'] = filtered_df['DEPARTURE_DELAY'] + filtered_df['ARRIVAL_DELAY']
        agg_df = filtered_df.groupby('AIRLINE_NAME').agg({'TOTAL_DELAY': 'sum'}).reset_index()

        # Sort and filter top 10
        if selected_category == 'least_delay':
            agg_df = agg_df.sort_values('TOTAL_DELAY', ascending=True).head(10)
            title = "Top 10 Airlines with Least Delay"
        else:
            agg_df = agg_df.sort_values('TOTAL_DELAY', ascending=False).head(10)
            title = "Top 10 Airlines with Highest Delay"

        x = agg_df['AIRLINE_NAME']
        y = agg_df['TOTAL_DELAY']

    elif selected_category in ['most_cancelled', 'most_diverted']:
        col = 'CANCELLED' if selected_category == 'most_cancelled' else 'DIVERTED'
        agg_df = filtered_df.groupby('AIRLINE_NAME').agg({col: 'sum'}).reset_index()

        # Sort and filter top 10
        agg_df = agg_df.sort_values(col, ascending=False).head(10)
        title = "Top 10 Airlines with Most Cancelled Flights" if col == 'CANCELLED' else "Top 10 Airlines with Most Diverted Flights"

        x = agg_df['AIRLINE_NAME']
        y = agg_df[col]

    # Create bar chart
    fig = px.bar(
        x=x,
        y=y,
        labels={'x': 'Airlines', 'y': 'Count'},
        title=title
    )
    fig.update_layout(xaxis_title="Airlines", yaxis_title="Count")

    return fig



if __name__ == "__main__":
    app.run_server(debug=True)
