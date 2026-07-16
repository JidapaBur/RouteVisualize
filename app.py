from __future__ import annotations

import pandas as pd
import streamlit as st
import folium
import plotly.express as px
from streamlit_folium import st_folium


st.set_page_config(
    page_title="SKF Route Dashboard",
    page_icon="🚚",
    layout="wide"
)


@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)

    df["Delivery Date"] = pd.to_datetime(
        df["Delivery Date"],
        dayfirst=True,
        errors="coerce"
    )

    # แยก Lat_Long เป็น latitude และ longitude
    latlon = (
        df["Lat_Long"]
        .astype(str)
        .str.extract(
            r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$"
        )
    )

    df["lat"] = pd.to_numeric(latlon[0], errors="coerce")
    df["lon"] = pd.to_numeric(latlon[1], errors="coerce")

    for c in ["BOX", "Pallet", "Round", "Drop", "NO"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # ตัดแถวที่ไม่มีวันที่ Trip หรือพิกัด
    df = df.dropna(
        subset=["Delivery Date", "Trip no", "lat", "lon"]
    ).copy()

    # รวมข้อมูลระดับ Invoice ให้เหลือหนึ่งแถวต่อ Delivery Stop
    stop = (
        df.groupby(
            [
                "Delivery Date",
                "Trip no",
                "Round",
                "Drop",
                "lat",
                "lon"
            ],
            as_index=False
        )
        .agg(
            BOX=("BOX", "sum"),
            Pallet=("Pallet", "sum"),
            Customer=("Customer Name", "first"),
            Truck=("TruckNo", "first"),
            Driver=("Driver Name", "first"),
            Invoice=("Invoice", "nunique")
        )
        .sort_values(
            ["Delivery Date", "Trip no", "Round", "Drop"]
        )
    )

    return df, stop


st.sidebar.title("SKF Dashboard")

uploaded = st.sidebar.file_uploader(
    "Upload SKF Excel",
    type=["xlsx", "xls"]
)

if uploaded is None:
    st.info("Please upload SKF_DATA.xlsx")
    st.stop()


raw, stop = load_excel(uploaded)

dates = sorted(stop["Delivery Date"].dt.date.unique())

selected_date = st.sidebar.selectbox(
    "Delivery Date",
    dates
)

stop = stop[
    stop["Delivery Date"].dt.date == selected_date
].copy()

trip_list = sorted(stop["Trip no"].unique())

selected_trip = st.sidebar.multiselect(
    "Trip",
    trip_list,
    default=trip_list
)

stop = stop[
    stop["Trip no"].isin(selected_trip)
].copy()

if stop.empty:
    st.warning("No data found for the selected date and trip.")
    st.stop()


# KPI
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Trips",
    stop["Trip no"].nunique()
)

c2.metric(
    "Drops",
    stop[["Trip no", "Drop"]]
    .drop_duplicates()
    .shape[0]
)

c3.metric(
    "BOX",
    f"{stop['BOX'].sum():,.0f}"
)

c4.metric(
    "Pallet",
    f"{stop['Pallet'].sum():,.0f}"
)


# สร้างแผนที่
m = folium.Map(
    location=[
        stop["lat"].mean(),
        stop["lon"].mean()
    ],
    zoom_start=9,
    tiles="CartoDB positron",
    control_scale=True
)

colors = [
    "red",
    "blue",
    "green",
    "purple",
    "orange",
    "black",
    "cadetblue"
]


for idx, (trip, g) in enumerate(
    stop.groupby("Trip no", sort=False)
):
    g = g.sort_values(
        ["Round", "Drop"]
    ).copy()

    color = colors[idx % len(colors)]

    coords = g[
        ["lat", "lon"]
    ].values.tolist()

    # เส้นทางของแต่ละ Trip
    if len(coords) >= 2:
        folium.PolyLine(
            locations=coords,
            color=color,
            weight=5,
            opacity=0.8,
            tooltip=(
                f"{trip} | "
                f"BOX {g['BOX'].sum():,.0f} | "
                f"Pallet {g['Pallet'].sum():,.0f}"
            )
        ).add_to(m)

    # Marker แบบ DivIcon จึงไม่เกิดปัญหารูป Marker โหลดไม่ขึ้น
    for _, r in g.iterrows():

        customer = (
            str(r.Customer)
            if pd.notna(r.Customer)
            else "-"
        )

        popup_html = f"""
        <div style="width:260px;">
            <b>{trip}</b><br>
            Round: {int(r.Round)}<br>
            Drop: {int(r.Drop)}<br>
            Customer: {customer}<br>
            BOX: {r.BOX:,.0f}<br>
            Pallet: {r.Pallet:,.0f}<br>
            Invoices: {int(r.Invoice)}<br>
            Truck: {r.Truck}<br>
            Driver: {r.Driver}
        </div>
        """

        marker_html = f"""
        <div style="
            background-color:{color};
            color:white;
            border-radius:50%;
            width:30px;
            height:30px;
            line-height:26px;
            text-align:center;
            font-size:13px;
            font-weight:bold;
            border:2px solid white;
            box-shadow:0 1px 5px rgba(0,0,0,0.45);
        ">
            {int(r.Drop)}
        </div>
        """

        folium.Marker(
            location=[
                r.lat,
                r.lon
            ],
            tooltip=(
                f"{trip} | "
                f"Drop {int(r.Drop)} | "
                f"{customer}"
            ),
            popup=folium.Popup(
                popup_html,
                max_width=300
            ),
            icon=folium.DivIcon(
                html=marker_html
            )
        ).add_to(m)


# ปรับ Zoom ให้ครอบคลุมทุกจุด
m.fit_bounds(
    [
        [
            stop["lat"].min(),
            stop["lon"].min()
        ],
        [
            stop["lat"].max(),
            stop["lon"].max()
        ]
    ],
    padding=(30, 30)
)


left, right = st.columns(
    [2, 1]
)

with left:
    st.subheader("Route Map")

    st_folium(
        m,
        height=650,
        use_container_width=True,
        returned_objects=[]
    )


with right:
    st.subheader("Trip Summary")

    summary = (
        stop.groupby(
            "Trip no",
            as_index=False
        )
        .agg(
            BOX=("BOX", "sum"),
            Pallet=("Pallet", "sum"),
            Drops=("Drop", "nunique")
        )
    )

    fig = px.bar(
        summary.sort_values("BOX"),
        x="BOX",
        y="Trip no",
        orientation="h",
        text_auto=".0f",
        hover_data=[
            "Pallet",
            "Drops"
        ],
        labels={
            "Trip no": "Trip no",
            "BOX": "BOX"
        }
    )

    fig.update_layout(
        height=580,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10
        ),
        showlegend=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


st.subheader("Delivery Stop Summary")

st.dataframe(
    stop,
    use_container_width=True,
    hide_index=True
)


csv = stop.to_csv(
    index=False
).encode("utf-8-sig")

st.download_button(
    label="Download Summary",
    data=csv,
    file_name=(
        f"SKF_Stop_Summary_"
        f"{selected_date}.csv"
    ),
    mime="text/csv"
)
