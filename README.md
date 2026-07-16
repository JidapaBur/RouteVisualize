from pathlib import Path
import pypandoc

md = r"""# 🚚 SKF Logistics Route Dashboard

A Streamlit dashboard for visualizing daily transportation routes, delivery volume, and logistics KPIs from SKF delivery data.

## Features

- 📅 Filter by Delivery Date
- 🚛 Filter by Trip Number
- 🗺 Interactive Route Map
- 📍 Numbered Delivery Stops
- 📦 BOX / Pallet Volume Analysis
- 📈 Daily KPI Dashboard
- 👤 Driver & Truck Summary
- 📊 Trip Summary
- 📥 Export filtered data

---

## Project Structure

```text
SKF_Route_Dashboard/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── config/
├── data/
├── pages/
├── utils/
├── assets/
└── .streamlit/
