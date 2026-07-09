# ==========================================
# 3. DATA LOADING & UNIFICATION
# ==========================================
@st.cache_data
def load_and_combine_data(folder_path):
    files = {
        'opex': 'Cleaned_Price_Cap_Data.csv',
        'whole': 'wholesale_allowances_cleaned.csv',
        'policy': 'policy_costs_cleaned.csv',
        'net': 'network_costs_cleaned.csv'
    }
    
    dfs = []
    for key, file in files.items():
        filepath = os.path.join(folder_path, file)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            
            # A. SCRUB WHITESPACES FIRST: Strip hidden spaces from key columns
            for col in ['Fuel Type', 'Charge Type', 'Payment Method', 'Allowance']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            
            # B. Apply Standardization Mappings
            if 'Fuel Type' in df.columns:
                df['Fuel Type'] = df['Fuel Type'].replace(FUEL_MAPPING)
                
            if 'Charge Type' in df.columns:
                df['Charge Type'] = df['Charge Type'].replace({'UR': 'Unit Rate', 'SC': 'Standing Charge'})
                
            if 'Start Date' not in df.columns and 'Cap Period' in df.columns:
                df['Start'] = df['Cap Period'].astype(str).str.split('-').str[0].str.strip()
                df['Start Date'] = pd.to_datetime(df['Start'], format='%B %Y', errors='coerce').fillna(
                                   pd.to_datetime(df['Start'], format='%b %Y', errors='coerce'))
            elif 'Start Date' in df.columns:
                df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
                
            if 'Allowance' in df.columns:
                df['Allowance_Full'] = df['Allowance'].map(ALLOWANCE_DICT).fillna(df['Allowance'])
                
            # If payment method is entirely missing or was converted to string 'nan', set to 'All'
            if 'Payment Method' not in df.columns or df['Payment Method'].isnull().all() or (df['Payment Method'] == 'nan').all():
                df['Payment Method'] = 'All' 
                
            dfs.append(df)
        else:
            st.sidebar.warning(f"Missing file: {file}")
            
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

@st.cache_data
def load_benchmark(folder_path):
    filepath = os.path.join(folder_path, 'total_bill_cleaned.csv')
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        
        # Scrub whitespaces here too
        for col in ['Fuel Type', 'Charge Type', 'Payment Method']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                
        if 'Fuel Type' in df.columns:
            df['Fuel Type'] = df['Fuel Type'].replace(FUEL_MAPPING)
        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        return df
    return pd.DataFrame()

folder_path = 'mastertrackerapp/'
df_master = load_and_combine_data(folder_path)
df_bench = load_benchmark(folder_path)
