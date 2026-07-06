import requests
from bs4 import BeautifulSoup
import pandas as pd
import io

# 1. Target the Ofgem Page
OFGEM_URL = "https://www.ofgem.gov.uk/information-consumers/energy-advice-households/energy-price-cap-unit-rates-and-standing-charges"

def get_latest_excel_link():
    """Scrapes the Ofgem page to find the latest regional rates Excel file."""
    print("Visiting Ofgem website...")
    response = requests.get(OFGEM_URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'regional' in href.lower() and href.endswith('.xlsx'):
            full_url = href if href.startswith('http') else f"https://www.ofgem.gov.uk{href}"
            print(f"Found latest file: {full_url}")
            return full_url
    print("No new regional Excel file found on the page.")
    return None

def process_and_update_data(excel_url):
    """Downloads, unpivots, cleans, and appends the new data to history.csv"""
    print("Downloading Excel file...")
    file_content = requests.get(excel_url).content
    
    # Read our existing historical database
    history_df = pd.read_csv('history.csv')
    
    try:
        # FIX 2: Updated Ofgem Tab Names
        # skiprows=2 is used because Ofgem usually has 2-3 rows of preamble text at the top of their sheets.
        # If the script fails to find the 'Fuel' column, adjust skiprows to 1, 3, or 4.
        print("Extracting tabs...")
        df_dd = pd.read_excel(io.BytesIO(file_content), sheet_name='2a Historical_Other', skiprows=2)
        df_sc = pd.read_excel(io.BytesIO(file_content), sheet_name='2b Historical_SC', skiprows=2)
        df_ppm = pd.read_excel(io.BytesIO(file_content), sheet_name='2c Historical_PPM', skiprows=2)
        
        # Standardize SC Region column
        if 'Charge Restriction Region' in df_sc.columns:
            df_sc = df_sc.rename(columns={'Charge Restriction Region': 'Region'})
            
        # Combine
        df_master = pd.concat([df_dd, df_sc, df_ppm], ignore_index=True)
        
        # Define our core columns
        id_columns = ['Fuel', 'Metering Arrangement', 'Charge Type', 'Payment Method', 'Region']
        
        # FIX 3: The Merged Cell Fix (Forward Fill)
        # This fills down the blank rows caused by Excel's merged cells
        df_master[id_columns] = df_master[id_columns].ffill()
        
        # FIX 1: Rename "Other" to "DD"
        df_master['Payment Method'] = df_master['Payment Method'].replace({'Other': 'DD', 'Other Payment Method': 'DD'})
        
        # Isolate the period columns (ignoring any hidden "Unnamed" columns pandas picks up)
        period_columns = [col for col in df_master.columns if col not in id_columns and not str(col).startswith('Unnamed')]
        
        # Unpivot (Melt)
        new_long_df = pd.melt(
            df_master,
            id_vars=id_columns,
            value_vars=period_columns,
            var_name='Period',
            value_name='Cost Value'
        )
        
        # Clean the numbers
        new_long_df = new_long_df.dropna(subset=['Cost Value'])
        new_long_df['Cost Value'] = pd.to_numeric(new_long_df['Cost Value'], errors='coerce')
        new_long_df = new_long_df.dropna(subset=['Cost Value'])
        
        # FIX 4: The Historical Data Filter
        # 1. Strip out anything containing older years just in case
        new_long_df = new_long_df[~new_long_df['Period'].str.contains('2019|2020|2021', na=False)]
        
        # 2. Only keep periods that DO NOT already exist in our history.csv
        existing_periods = history_df['Period'].unique()
        new_data = new_long_df[~new_long_df['Period'].isin(existing_periods)]
        
        # Append logic
        if new_data.empty:
            print("No new price cap periods found. Database is already up to date.")
        else:
            print(f"Found {len(new_data['Period'].unique())} new period(s)! Appending to master database...")
            updated_history = pd.concat([history_df, new_data], ignore_index=True)
            updated_history.to_csv('history.csv', index=False)
            print("Update complete! history.csv overwritten with new data.")
            
    except Exception as e:
        print(f"Data extraction failed. Ofgem may have changed their Excel format. Error: {e}")

if __name__ == "__main__":
    latest_link = get_latest_excel_link()
    if latest_link:
        process_and_update_data(latest_link)
