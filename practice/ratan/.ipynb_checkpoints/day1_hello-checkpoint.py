import streamlit as st
import pandas as pd

st.header("Curatr-home")
st.caption("progress panel")

practice_df = pd.DataFrame({
    "media_type": ["movie", "movie", "tv"],
    "title": ["Sample A", "Sample B", "Sample C"],
    "release_year": [2018, 2021, 2024],
    "rating": [7.2, 8.1, 6.9]
})

st.dataframe(practice_df)