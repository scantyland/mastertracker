import requests
from bs4 import BeautifulSoup
import urllib.parse
import pandas as pd
import numpy as np
import os

# =====================================================================
# 1. THE SCRAPER (Extract)
# =====================================================================
ofgem_url = "https://www.ofgem.gov.uk/energy-regulation/domestic-and-non-domestic/energy-pricing-rules/energy-price-cap/energy-price-cap-default-tariff-levels"
print(f"Visiting Ofgem URL: {ofgem_url}")

response = requests.get(ofgem_url)
soup = BeautifulSoup(response.content, 'html.parser')

target_file_name = "downloaded_cap_rates.xlsx" 
download_link = None

for a_tag in soup.find_all('a', href=True):
    link_text = a_tag.text.strip().lower() 
    if link_text.startswith("final levelised cap rate models"):
        download_link = a_tag['href']
        print(f"Found matching file link text: '{a_tag.text.strip()}'")
        break

if not download_link:
    print("Error: Could not find a file starting with 'Final levelised cap rate models' on the webpage.")
    exit()

if download_link.startswith('/'):
    download_link = urllib.parse.urljoin("https://www.ofgem.gov.uk", download_link)

print(f"Downloading from: {download_link}")

file_response = requests.get(download_link)
with open(target_file_name, 'wb') as f:
    f.write(file_response.content)

print("Download complete. Starting data extraction and cleaning...")

# =====================================================================
# 2. THE CLEANER (Transform)
# =====================================================================
try:
    print("Loading sheet: '3e Historical level inputs'...")
    df_raw = pd.read_excel(target_file_name, sheet_name='3e Historical level inputs', header=None, engine='openpyxl')
except Exception as e:
    print(f"Error loading the specific sheet. Details: {e}")
    exit()

# A. Find date row
date_row_idx = 0
for idx, row in df_raw.head(15).iterrows():
    row_text = ' '.join(row.astype(str).tolist())
    if ('202' in row_text or '203' in row_text) and ('Oct' in row_text or 'Jan' in row_text or 'Apr' in row_text or 'Jul' in row_text):
        date_row_idx = idx
        break

# B. Capture Allowances
dynamic_allowance_list = []
raw_allowance_col = df_raw.iloc[date_row_idx + 1:, 0] 

for val in raw_allowance_col:
    val_str = str(val).strip()
    if val_str.lower() not in ['nan', 'none', ''] and 'total' not in val_str.lower():
        if val_str not in dynamic_allowance_list:
            dynamic_allowance_list.append(val_str)

# C. Capture Cap Periods
dynamic_periods = []
for val in df_raw.iloc[date_row_idx]:
    val_str = str(val).strip()
    if ('202' in val_str or '203' in val_str) and val_str not in dynamic_periods:
        dynamic_periods.append(val_str.lower())

records = []
current_payment_method = 'Unknown'
current_fuel_type = {}
current_charge_type = {}
current_period = {}

# D. Scan document cell by cell
for r_idx in range(len(df_raw)):
    row = df_raw.iloc[r_idx]
    is_data_row = False
    allowance_name = None
    
    for cell_val in row:
        val_str = str(cell_val).strip()
        if val_str in dynamic_allowance_list:
            is_data_row = True
            allowance_name = val_str
            break
            
    if is_data_row:
        for c_idx in range(len(row)):
            val = row[c_idx]
            if pd.isna(val) or str(val).strip() == '' or str(val).strip() in dynamic_allowance_list:
                continue
                
            period = current_period.get(c_idx)
            if not period: continue 
            
            fuel = current_fuel_type.get(c_idx, 'Unknown')
            charge = current_charge_type.get(c_idx, 'Unknown')
            
            records.append({
                'Payment Method': current_payment_method,
                'Fuel Type': fuel,
                'Charge Type': charge,
                'Allowance': allowance_name,
                'Cap Period': period,
                'Raw Value': val
            })
    else:
        # UPDATED: Mapping 'Other' to Direct Debit
        for c_val in row:
            c_str = str(c_val).lower().strip()
            if c_str == 'other' or 'direct debit' in c_str: current_payment_method = 'Direct Debit'
            elif 'standard credit' in c_str: current_payment_method = 'Standard Credit'
            elif 'ppm' in c_str or 'prepayment' in c_str: current_payment_method = 'PPM'
        
        last_fuel, last_charge, last_period = None, None, None
        
        for c_idx in range(len(row)):
            cell_val = str(row[c_idx]).strip()
            cell_lower = cell_val.lower()
            
            if pd.isna(row[c_idx]) or cell_val == '' or cell_val == 'nan':
                if last_fuel: current_fuel_type[c_idx] = last_fuel
                if last_charge: current_charge_type[c_idx] = last_charge
                if last_period: current_period[c_idx] = last_period
                continue
            
            found_fuel = False
            if 'single' in cell_lower: last_fuel = 'Electricity Single-Rate'; found_fuel = True
            elif 'multi' in cell_lower: last_fuel = 'Electricity Multi-Register'; found_fuel = True
            elif 'gas' in cell_lower: last_fuel = 'Gas'; found_fuel = True
            elif 'dual' in cell_lower: last_fuel = 'Dual Fuel (implied)'; found_fuel = True
            if found_fuel: current_fuel_type[c_idx] = last_fuel
            
            # UPDATED: Mapping 'Nil consumption' and 'Typical consumption'
            found_charge = False
            if 'nil consumption' in cell_lower or 'standing charge' in cell_lower: 
                last_charge = 'Standing Charge'
                found_charge = True
            elif 'typical consumption' in cell_lower or 'unit rate' in cell_lower: 
                last_charge = 'Unit Rate'
                found_charge = True
            if found_charge: current_charge_type[c_idx] = last_charge
            
            found_period = False
            for p in dynamic_periods:
                if p in cell_lower:
                    last_period = cell_val 
                    found_period = True
                    break
            if found_period: current_period[c_idx] = last_period
            
            if not found_fuel and last_fuel: current_fuel_type[c_idx] = last_fuel
            if not found_charge and last_charge: current_charge_type[c_idx] = last_charge
            if not found_period and last_period: current_period[c_idx] = last_period

df = pd.DataFrame(records)

# =====================================================================
# 3. ISOLATE UNIT RATE & SAVE (Load)
# =====================================================================
if not df.empty:
    df['Raw Value'] = pd.to_numeric(df['Raw Value'], errors='coerce')
    df = df.dropna(subset=['Raw Value'])
    
    sc_df = df[df['Charge Type'] == 'Standing Charge'].copy()
    ur_df = df[df['Charge Type'] == 'Unit Rate'].copy()
    
    sc_df = sc_df.drop_duplicates(subset=['Payment Method', 'Fuel Type', 'Allowance', 'Cap Period'])
    ur_df = ur_df.drop_duplicates(subset=['Payment Method', 'Fuel Type', 'Allowance', 'Cap Period'])
    
    sc_df = sc_df.rename(columns={'Raw Value': 'SC_Value'})
    ur_df = ur_df.rename(columns={'Raw Value': 'Total_UR_Value'})  # This is the "Typical Consumption" value
    
    merged = pd.merge(
        ur_df,
        sc_df[['Payment Method', 'Fuel Type', 'Allowance', 'Cap Period', 'SC_Value']],
        on=['Payment Method', 'Fuel Type', 'Allowance', 'Cap Period'],
        how='left'
    )
    
    # Subtraction: Typical Consumption (Total Bill) - Nil Consumption (Standing Charge) = Unit Rate
    merged['SC_Value'] = merged['SC_Value'].fillna(0)
    merged['Isolated Unit Rate'] = merged['Total_UR_Value'] - merged['SC_Value']
    
    final_ur = merged.copy()
    final_ur['Charge Type'] = 'Unit Rate'
    final_ur['Cost Value'] = final_ur['Isolated Unit Rate']
    final_ur = final_ur[['Payment Method', 'Fuel Type', 'Charge Type', 'Allowance', 'Cap Period', 'Cost Value']]
    
    final_sc = sc_df.copy()
    final_sc['Charge Type'] = 'Standing Charge'
    final_sc['Cost Value'] = final_sc['SC_Value']
    final_sc = final_sc[['Payment Method', 'Fuel Type', 'Charge Type', 'Allowance', 'Cap Period', 'Cost Value']]
    
    final_df = pd.concat([final_sc, final_ur], ignore_index=True)
    final_df = final_df.sort_values(by=['Payment Method', 'Fuel Type', 'Charge Type', 'Cap Period', 'Allowance'])
    
    final_df.to_csv('Cleaned_Price_Cap_Data.csv', index=False)
    
    if os.path.exists(target_file_name):
        os.remove(target_file_name)
    print("Success! Streamlit CSV has been generated.")
else:
    print("Error: The extracted dataframe was empty. Check the formatting of the sheet.")
