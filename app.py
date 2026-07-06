import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("Data Detective Mode 🕵️‍♂️")

st.write("Let's look at exactly what Python sees in this file before we do any cleaning or math.")

try:
    # Read the raw file
    raw_data = pd.read_csv("Dashboard_Data - Sheet1.csv")
    
    st.markdown("### 1. The Raw Table")
    st.write("Look at the Cost Value column. Are there numbers, blanks, formulas, or weird symbols?")
    st.dataframe(raw_data)
    
    st.markdown("### 2. The Column Names")
    st.write("Are there any hidden spaces at the start or end of these names?")
    st.write(raw_data.columns.tolist())
    
    st.markdown("### 3. The Data Types")
    st.write("If Cost Value says 'object', Python thinks it's text. If it says 'float64', Python knows it's a number.")
    st.write(raw_data.dtypes.astype(str))

except Exception as e:
    st.error(f"Error reading the file: {e}")
