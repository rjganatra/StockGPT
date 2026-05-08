import streamlit as st
import pandas as pd

st.title("StockGPT Pro")

df = pd.read_csv("data/scans/latest_scan.csv")

st.dataframe(df)
