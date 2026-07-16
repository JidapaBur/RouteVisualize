from __future__ import annotations

import pandas as pd
import streamlit as st
import folium
import plotly.express as px
from streamlit_folium import st_folium

st.set_page_config(page_title="SKF Route Dashboard", layout="wide")

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df["Delivery Date"] = pd.to_datetime(df["Delivery Date"], dayfirst=True)

    latlon = df["Lat_Long"].astype(str).str.split(",", expand=True)
    df["lat"] = pd.to_numeric(latlon[0], errors="coerce")
    df["lon"] = pd.to_numeric(latlon[1], errors="coerce")

    for c in ["BOX","Pallet","Round","Drop","NO"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    stop = (
        df.groupby(
            ["Delivery Date","Trip no","Round","Drop","lat","lon"],
            as_index=False
        )
        .agg(
            BOX=("BOX","sum"),
            Pallet=("Pallet","sum"),
            Customer=("Customer Name","first"),
            Truck=("TruckNo","first"),
            Driver=("Driver Name","first"),
            Invoice=("Invoice","nunique")
        )
        .sort_values(["Trip no","Round","Drop"])
    )
    return df, stop

st.sidebar.title("SKF Dashboard")

uploaded = st.sidebar.file_uploader(
    "Upload SKF Excel",
    type=["xlsx","xls"]
)

if uploaded is None:
    st.info("Upload SKF_DATA.xlsx")
    st.stop()

raw, stop = load_excel(uploaded)

dates = sorted(stop["Delivery Date"].dt.date.unique())
selected_date = st.sidebar.selectbox("Delivery Date", dates)

stop = stop[stop["Delivery Date"].dt.date == selected_date]

trip_list = sorted(stop["Trip no"].unique())
selected_trip = st.sidebar.multiselect(
    "Trip",
    trip_list,
    default=trip_list
)

stop = stop[stop["Trip no"].isin(selected_trip)]

c1,c2,c3,c4 = st.columns(4)
c1.metric("Trips", stop["Trip no"].nunique())
c2.metric("Drops", len(stop))
c3.metric("BOX", f"{stop['BOX'].sum():,.0f}")
c4.metric("Pallet", f"{stop['Pallet'].sum():,.0f}")

m = folium.Map(
    location=[stop["lat"].mean(), stop["lon"].mean()],
    zoom_start=9
)

colors = [
    "red","blue","green","purple",
    "orange","black","cadetblue"
]

for idx,(trip,g) in enumerate(stop.groupby("Trip no")):
    g = g.sort_values(["Round","Drop"])
    color = colors[idx % len(colors)]

    coords = g[["lat","lon"]].values.tolist()

    folium.PolyLine(
        coords,
        color=color,
        weight=5,
        tooltip=f"{trip}"
    ).add_to(m)

    for _,r in g.iterrows():
        folium.Marker(
            [r.lat,r.lon],
            tooltip=f"{trip} | Drop {int(r.Drop)}",
            popup=f"""
Customer : {r.Customer}<br>
BOX : {r.BOX}<br>
Pallet : {r.Pallet}<br>
Invoices : {r.Invoice}
"""
        ).add_to(m)

left,right = st.columns([2,1])

with left:
    st.subheader("Route Map")
    st_folium(m,height=650,use_container_width=True)

with right:
    st.subheader("Trip Summary")

    summary = (
        stop.groupby("Trip no",as_index=False)
        .agg(
            BOX=("BOX","sum"),
            Pallet=("Pallet","sum"),
            Drops=("Drop","nunique")
        )
    )

    fig = px.bar(
        summary.sort_values("BOX"),
        x="BOX",
        y="Trip no",
        orientation="h",
        text_auto=True
    )

    st.plotly_chart(fig,use_container_width=True)

st.subheader("Delivery Stop Summary")
st.dataframe(stop,use_container_width=True,hide_index=True)

csv = stop.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Download Summary",
    csv,
    "SKF_Stop_Summary.csv",
    "text/csv"
)
