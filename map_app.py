import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 1. Page Configuration & Hidden URL Password
st.set_page_config(page_title="Regional Price Cap Map", layout="wide")

# Check for the hidden URL password
# url_password = st.query_params.get("pwd", "")
# if url_password != st.secrets["app_password"]:
  #  st.error("🔒 Unauthorized Access. Please view this dashboard through the secure internal company portal.")
  #  st.stop()

st.title("🗺️ Regional Price Cap Tracker")
st.write("Interactive view of standing charges and unit rates across UK regions.")

# 2. Load the Historical Data
@st.cache_data
def load_history():
    return pd.read_csv("history.csv")

history_df = load_history()

# 3. Create the Interactive Drop-Down Filters
col1, col2, col3, col4 = st.columns(4)

with col1:
    map_period = st.selectbox("Select Cap Period:", options=history_df["Period"].unique())
with col2:
    map_fuel = st.selectbox("Select Fuel Type:", options=history_df["Fuel"].unique())
with col3:
    map_payment = st.selectbox("Select Payment Method:", options=history_df["Payment Method"].unique())
with col4:
    map_charge = st.selectbox("Select Charge Type:", options=history_df["Charge Type"].unique())

# 4. Filter the Data Based on User Selection
map_filtered_df = history_df[
    (history_df["Period"] == map_period) & 
    (history_df["Fuel"] == map_fuel) & 
    (history_df["Payment Method"] == map_payment) & 
    (history_df["Charge Type"] == map_charge)
].copy()

# 5. Load the GeoJSON Digital Stencil and Build the Map
try:
    with open("uk_regions.geojson", "r") as f:
        uk_geojson = json.load(f)
        
    fig_map = px.choropleth_mapbox(
        map_filtered_df,
        geojson=uk_geojson,
        locations="Region",
        featureidkey="properties.name", # Ensure this matches the property name in your GeoJSON
        color="Cost Value",
        color_continuous_scale="Viridis",
        mapbox_style="carto-positron",
        zoom=4.5,
        center={"lat": 54.5, "lon": -2.0},
        opacity=0.7,
        labels={"Cost Value": "Cap Value (£)"}
    )

    fig_map.update_layout(
        margin={"r":0, "t":0, "l":0, "b":0},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig_map, use_container_width=True)

except FileNotFoundError:
    st.warning("⚠️ uk_regions.geojson file not found. Please upload the spatial boundaries to GitHub to render the map.")
    st.dataframe(map_filtered_df) # Show the raw data table as a fallback
