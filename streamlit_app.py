import streamlit as st
import pandas as pd
from datetime import datetime
import json
from scraper import scrape_from_csv

st.set_page_config(page_title="Product Scraper from CSV")
st.title("Product Scraper from CSV 🛒")

# Sidebar Input/Settings
st.sidebar.title("Scraper Settings")
model_selection = st.sidebar.selectbox(
    "Select Model", 
    options=["gpt-4o-mini", "gpt-4o-2024-08-06"], 
    index=0
)

# Upload CSV File Option
csv_file = st.sidebar.file_uploader("Upload CSV File with URLs", type="csv")

# Extraction Prompt Input
prompt_input = st.sidebar.text_area(
    "Enter Prompt", 
    value="Please extract one product name and its price from the content provided."
)

# Button to Trigger Scraping
if csv_file and st.sidebar.button("Scrape"):
    try:
        csv_data = pd.read_csv(csv_file)
        urls = csv_data['URL'].dropna().tolist()

        results = scrape_from_csv(urls, prompt_input, model_selection)

        results_df = pd.DataFrame(results)
        st.write("Scraped Results:")
        st.dataframe(results_df)

        # Save Results to CSV Option
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_csv_path = f"{timestamp}_scraped_products.csv"
        results_df.to_csv(results_csv_path, index=False)
        st.download_button(
            "Download Results CSV",
            data=results_df.to_csv(index=False),
            file_name=results_csv_path
        )

        st.success(f"Scraping completed successfully! Data saved as {results_csv_path}")
    except Exception as e:
        st.error(f"An error occurred during scraping: {e}")