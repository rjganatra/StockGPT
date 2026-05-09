import streamlit as st
import pandas as pd
from pathlib import Path

st.title("StockGPT")

scan_file = Path("data/scans/latest_scan.csv")

if scan_file.exists():

    df = pd.read_csv(scan_file)

    st.subheader("Latest Scan")

    st.dataframe(df)

else:

    st.warning("No scan data available yet. Run scanner first.")
