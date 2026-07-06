import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import datetime

# 1. Target the Ofgem Page
OFGEM_URL = "https://www.ofgem.gov.uk/information-consumers/energy-advice-households/energy-price-cap-unit-rates-and-standing-charges"

def get_latest_excel_link():
    """Scrapes the Ofgem page to find the latest regional rates Excel file."""
    print("Visiting Ofgem website...")
    response = requests.get(OFGEM_URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Hunt for the specific Annex file containing regional rates
    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'regional' in href.lower() and href.endswith('.xlsx'):
            full_url = href if href.startswith('http') else f"https://www.ofgem.gov.uk{href}"
            print(f"Found latest file: {full_url}")
            return full_url
    print("No new regional Excel file found on the page.")
    return None

def process_and_update_data(excel_url):
    """Downloads, unpivots, and appends the new data to history.csv"""
    print("Downloading Excel file...")
    file_content = requests.get(excel_url).content
    
    # Read the historical database
    history_df = pd.read_csv('history.csv')
    
    try:
        # NOTE: Ofgem tab names might change slightly quarter to quarter. 
        # The script looks for the standard DD, SC, and PPM tabs.
        print("Extracting tabs...")
        df_dd = pd.read_excel(io.BytesIO(file_content), sheet_name='DD - Historic')
        df_sc = pd.read_excel(io.BytesIO(file_content), sheet_name='SC - Historic')
        df_ppm = pd.read_excel(io.BytesIO(file_content), sheet_name='PPM - Historic')
        
        # Standardize SC Region column
        if 'Charge Restriction Region' in df_sc.columns:
            df_sc = df_sc.rename(columns={'Charge Restriction Region': 'Region'})
            
        # Combine
        df_master = pd.concat([df_dd, df_sc, df_ppm], ignore_index=True)
        
        # Unpivot (Melt)
        id_columns = ['Fuel', 'Metering Arrangement', 'Charge Type', 'Payment Method', 'Region']
        period_columns = [col for col in df_master.columns if col not in id_columns]
        
        new_long_df = pd.melt(
            df_master,
            id_vars=id_columns,
            value_vars=period_columns,
            var_name='Period',
            value_name='Cost Value'
        )
        
        # Clean
        new_long_df = new_long_df.dropna(subset=['Cost Value'])
        new_long_df['Cost Value'] = pd.to_numeric(new_long_df['Cost Value'], errors='coerce')
        
        # Append to history and drop any duplicates (in case the script runs twice on the same file)
        print("Appending to master database...")
        updated_history = pd.concat([history_df, new_long_df], ignore_index=True)
        updated_history = updated_history.drop_duplicates()
        
        updated_history.to_csv('history.csv', index=False)
        print("Update complete! history.csv overwritten with new data.")
        
    except Exception as e:
        print(f"Data extraction failed. Ofgem may have changed their Excel format. Error: {e}")

if __name__ == "__main__":
    latest_link = get_latest_excel_link()
    if latest_link:
        process_and_update_data(latest_link)
