import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# ==========================================
# 1. PAGE CONFIGURATION & METADATA
# ==========================================
st.set_page_config(page_title="Scenario Engine", layout="wide", page_icon="📈")
st.title("📈 Regulatory Consultation Scenario Engine")
st.markdown("Test up to 4 specific scenarios for a target policy, while applying up to 2 interacting global changes to the baseline bill.")

ALLOWANCE_DICT = {
    'DF': 'Direct Fuel Cost', 'Direct Fuel': 'Direct Fuel Cost', 
    'CM': 'Capacity Market', 'AA': 'Adjustment Allowance', 
    'PC': 'Policy Costs', 'NC': 'Network Costs', 'OC': 'Operating Costs (Legacy)', 
    'CO': 'Core Operating Costs', 'SMNCC': 'Smart Metering Net Cost Change', 
    'IC': 'Industry Charges', 'PAAC': 'Payment Method Uplift (Fixed)', 
    'PAP': 'Payment Method Uplift (Variable)', 'DRC': 'Debt-Related Costs', 
    'EBIT': 'Earnings Before Interest and Tax', 'HAP': 'Headroom Allowance Percentage', 
    'RO': 'Renewables Obligation (RO)', 'FiT': 'Feed-in Tariff (FiT)', 
    'ECO': 'Energy Company Obligation (ECO)', 'WHD': 'Warm Home Discount (WHD)', 
    'WHD (unit rate)': 'Warm Home Discount (Unit Rate)', 
    'AAHEDC': 'Assistance for Areas with High Electricity Distribution Costs', 
    'NCC': 'Network Charging Compensation', 'nRAB': 'Nuclear Regulated Asset Base', 
    'GGL': 'Green Gas Levy (GGL)',
    'CfD': 'Contracts for Difference (CfD)', 'Backwardation': 'Backwardation', 
    'Gas Transmission': 'Gas Transmission', 'Gas Distribution': 'Gas Distribution', 
    'TNUoS': 'Transmission Network Use of System (TNUoS)', 
    'BSUoS': 'Balancing Services Use of System (BSUoS)', 
    'DUoS': 'Distribution Use of System (DUoS)', 'Levelisation': 'Levelisation'
}

TAB_GROUPINGS = {
    "Wholesale": ['Direct Fuel Cost', 'Backwardation', 'Capacity Market', 'Contracts for Difference (CfD)'],
    "Policy": ['Renewables Obligation (RO)', 'Feed-in Tariff (FiT)', 'Energy Company Obligation (ECO)', 
               'Warm Home Discount (WHD)', 'Warm Home Discount (Unit Rate)', 'Assistance for Areas with High Electricity Distribution Costs', 
               'Network Charging Compensation', 'Nuclear Regulated Asset Base', 'Green Gas Levy (GGL)'],
    "Network": ['Transmission Network Use of System (TNUoS)', 'Distribution Use of System (DUoS)', 
                'Balancing Services Use of System (BSUoS)', 'Gas Distribution', 'Gas Transmission'],
    "OPEX": ['Operating Costs (Legacy)', 'Core Operating Costs', 'Debt-Related Costs', 'Industry Charges', 
             'Earnings Before Interest and Tax', 'Smart Metering Net Cost Change', 'Headroom Allowance Percentage'],
    "Other Costs": ['Adjustment Allowance', 'Payment Method Uplift (Fixed)', 'Payment Method Uplift (Variable)', 'Levelisation']
}

FUEL_MAPPING = {
    'Electricity Single Rate': 'Electricity Single-Rate',
    'Electricity- Single-Rate': 'Electricity Single-Rate',
    'Electricity - Single-Rate': 'Electricity Single-Rate',
    'Electricity - Single Rate': 'Electricity Single-Rate',
    'Electricity - Multi-Register': 'Electricity Multi-Register',
    'Electricity Multi Register': 'Electricity Multi-Register',
    'Non-PPM gas': 'Gas',
    'Gas': 'Gas',
    'Dual Fuel': 'Dual Fuel (implied)',
    'Dual Fuel (implied)': 'Dual Fuel (implied)'
}

DEFAULT_TDCV = {"Gas": 11500, "Electricity Single-Rate": 2900, "Electricity Multi-Register": 2900}
BUCKETS = ["Wholesale", "Policy", "Network", "OPEX", "Other Costs"]

# ==========================================
# 2. DATA LOADING & FILTERING
# ==========================================
@st.cache_data
def load_baseline_data():
    files = ['Cleaned_Price_Cap_Data.csv', 'wholesale_allowances_cleaned.csv', 'policy_costs_cleaned.csv', 'network_costs_cleaned.csv']
    possible_folders = ['', 'mastertrackerapp/']
    dfs = []
    
    for f in files:
        file_loaded = False
        for folder in possible_folders:
            filepath = os.path.join(folder, f)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                for col in ['Fuel Type', 'Charge Type', 'Payment Method', 'Allowance', 'Cap Period']:
                    if col in df.columns:
                        df[col] = df[col].astype(str).str.strip()
                if 'Fuel Type' in df.columns:
                    df['Fuel Type'] = df['Fuel Type'].replace(FUEL_MAPPING)
                if 'Allowance' in df.columns:
                    df['Allowance_Full'] = df['Allowance'].map(ALLOWANCE_DICT).fillna(df['Allowance'])
                if 'Payment Method' not in df.columns or df['Payment Method'].isnull().all() or (df['Payment Method'] == 'nan').all():
                    df['Payment Method'] = 'All' 
                if 'Cap Period' in df.columns:
                    df['Temp_Start'] = df['Cap Period'].astype(str).str.split('-').str[0].str.strip()
                    df['Parsed_Date'] = pd.to_datetime(df['Temp_Start'], errors='coerce')
                    
                dfs.append(df)
                file_loaded = True
                break
                
    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        max_date = combined['Parsed_Date'].max()
        return combined[combined['Parsed_Date'] == max_date].copy()
    return pd.DataFrame()

df_baseline = load_baseline_data()

# ==========================================
# 3. SIDEBAR (GLOBAL SETTINGS & TDCV)
# ==========================================
st.sidebar.header("1. Global Settings")
fuel_options = ["Dual Fuel", "Electricity Single-Rate", "Electricity Multi-Register", "Gas"]
selected_fuel = st.sidebar.selectbox("Fuel Type Profile", options=fuel_options)

payment_options = ["Direct Debit", "Standard Credit", "PPM"]
selected_payment = st.sidebar.selectbox("Payment Method", options=payment_options)

st.sidebar.divider()
st.sidebar.header("2. TDCV Settings")
is_dual_fuel = (selected_fuel == "Dual Fuel")

if is_dual_fuel:
    custom_tdcv_elec = st.sidebar.number_input("New TDCV (Electricity)", value=DEFAULT_TDCV["Electricity Single-Rate"], step=100)
    custom_tdcv_gas = st.sidebar.number_input("New TDCV (Gas)", value=DEFAULT_TDCV["Gas"], step=100)
    target_fuels = ['Electricity Single-Rate', 'Gas']
else:
    baseline_tdcv = DEFAULT_TDCV.get(selected_fuel, 2900)
    custom_tdcv = st.sidebar.number_input(f"New TDCV ({selected_fuel})", value=baseline_tdcv, step=100)
    target_fuels = [selected_fuel]

# Filter Baseline Data
df_filtered = df_baseline[
    (df_baseline['Fuel Type'].isin(target_fuels)) & 
    ((df_baseline['Payment Method'] == selected_payment) | (df_baseline['Payment Method'] == 'All'))
].copy()
valid_allowances = [item for sublist in TAB_GROUPINGS.values() for item in sublist]
df_filtered = df_filtered[df_filtered['Allowance_Full'].isin(valid_allowances)]

def get_bucket(allowance_name):
    for bucket, allowances in TAB_GROUPINGS.items():
        if allowance_name in allowances:
            return bucket
    return "Other Costs"

df_filtered['Bucket'] = df_filtered['Allowance_Full'].apply(get_bucket)
df_filtered['Charge Type'] = df_filtered['Charge Type'].replace({'UR': 'Unit Rate', 'SC': 'Standing Charge'})
df_filtered = df_filtered.groupby(['Bucket', 'Allowance_Full', 'Charge Type', 'Fuel Type'], as_index=False)['Cost Value'].sum()

# Helper for TDCV scaling
def apply_tdcv_scaling(val, charge_type, fuel_type):
    if charge_type == 'Unit Rate':
        if is_dual_fuel:
            if fuel_type == 'Gas': return val * (custom_tdcv_gas / DEFAULT_TDCV['Gas'])
            else: return val * (custom_tdcv_elec / DEFAULT_TDCV['Electricity Single-Rate'])
        else:
            return val * (custom_tdcv / baseline_tdcv)
    return val

# Create readable list of existing allowances for dropdowns
df_filtered['Dropdown_Label'] = df_filtered['Allowance_Full'] + " - " + df_filtered['Fuel Type'].str[:4] + " (" + df_filtered['Charge Type'] + ")"
allowance_lookup = df_filtered.set_index('Dropdown_Label').to_dict('index')
dropdown_options = ["None", "Create New Policy..."] + list(df_filtered['Dropdown_Label'].unique())

# ==========================================
# 4. SCENARIO BUILDER UI
# ==========================================
st.divider()

# --- PART A: GLOBAL INTERACTING ALLOWANCES ---
st.markdown("### 🔄 1. Global Interacting Allowances")
st.markdown("Select up to **two** policies you want to change alongside your scenarios. These changes apply equally to ALL scenarios.")

global_adjustments = []
col_g1, col_g2 = st.columns(2)

def render_allowance_editor(col_block, identifier):
    with col_block.container():
        selection = st.selectbox(f"Select Interacting Policy {identifier}", options=dropdown_options, key=f"sel_{identifier}")
        
        if selection == "Create New Policy...":
            with st.container():
                c1, c2, c3, c4 = st.columns(4)
                pol_name = c1.text_input("Name", value=f"New Policy {identifier}", key=f"n_{identifier}")
                pol_charge = c2.selectbox("Charge Type", ["Standing Charge", "Unit Rate"], key=f"c_{identifier}")
                pol_fuel = c3.selectbox("Fuel", ["Electricity Single-Rate", "Gas"] if is_dual_fuel else [selected_fuel], key=f"f_{identifier}")
                pol_val = c4.number_input("Value (£)", value=0.0, step=1.0, key=f"v_{identifier}")
                
                if pol_val != 0.0:
                    scaled_val = apply_tdcv_scaling(pol_val, pol_charge, pol_fuel)
                    global_adjustments.append({"Name": pol_name, "Change": scaled_val})
                    st.caption(f"**Applied globally:** +£{scaled_val:.2f} (scaled)")
                    
        elif selection != "None":
            base_data = allowance_lookup[selection]
            base_val = base_data['Cost Value']
            new_val = st.number_input(f"New Value for {selection}", value=float(base_val), step=1.0, key=f"v_{identifier}")
            
            # Calculate the Delta
            diff = new_val - base_val
            if diff != 0:
                scaled_diff = apply_tdcv_scaling(diff, base_data['Charge Type'], base_data['Fuel Type'])
                global_adjustments.append({"Name": base_data['Allowance_Full'], "Change": scaled_diff})
                st.caption(f"**Applied globally:** {('+£' if scaled_diff > 0 else '-£')}{abs(scaled_diff):.2f} variance (scaled)")

render_allowance_editor(col_g1, "A")
render_allowance_editor(col_g2, "B")

total_global_adj = sum(item["Change"] for item in global_adjustments)

# --- PART B: THE SCENARIO VARIABLE ---
st.divider()
st.markdown("### 🎯 2. The Scenario Variable")
st.markdown("Select **one specific policy** (e.g., Debt-Related Costs) to test across 4 different regulatory scenarios.")

scenario_var_sel = st.selectbox("Select Target Scenario Policy", options=dropdown_options, index=0)

scen_base_val = 0.0
scen_charge_type = "Standing Charge"
scen_fuel_type = selected_fuel

if scenario_var_sel == "Create New Policy...":
    sc1, sc2, sc3 = st.columns(3)
    scen_name = sc1.text_input("New Scenario Policy Name", value="Consultation Policy X")
    scen_charge_type = sc2.selectbox("Charge Type", ["Standing Charge", "Unit Rate"], key="scen_charge")
    scen_fuel_type = sc3.selectbox("Fuel", ["Electricity Single-Rate", "Gas"] if is_dual_fuel else [selected_fuel], key="scen_fuel")
elif scenario_var_sel != "None":
    scen_data = allowance_lookup[scenario_var_sel]
    scen_base_val = float(scen_data['Cost Value'])
    scen_charge_type = scen_data['Charge Type']
    scen_fuel_type = scen_data['Fuel Type']
    st.info(f"**Current Baseline for this policy:** £{scen_base_val:.2f}")

st.markdown("#### Input Scenario Values (£)")
scen_col1, scen_col2, scen_col3, scen_col4 = st.columns(4)
s1_val = scen_col1.number_input("Scenario 1 (£)", value=scen_base_val, step=1.0)
s2_val = scen_col2.number_input("Scenario 2 (£)", value=scen_base_val, step=1.0)
s3_val = scen_col3.number_input("Scenario 3 (£)", value=scen_base_val, step=1.0)
s4_val = scen_col4.number_input("Scenario 4 (£)", value=scen_base_val, step=1.0)

# ==========================================
# 5. MATHEMATICAL AGGREGATION
# ==========================================
# Calculate Baseline Total
df_filtered['Scaled Value'] = df_filtered.apply(lambda r: apply_tdcv_scaling(r['Cost Value'], r['Charge Type'], r['Fuel Type']), axis=1)
raw_baseline_total = df_filtered['Scaled Value'].sum()

# Baseline WITH Global Adjustments applied (so all scenarios start from the same adjusted floor)
adjusted_baseline = raw_baseline_total + total_global_adj

# Calculate Scenarios
def calc_scenario(scen_val):
    if scenario_var_sel == "None":
        return adjusted_baseline
    # Calculate the variance for this specific scenario
    diff = scen_val - scen_base_val
    scaled_diff = apply_tdcv_scaling(diff, scen_charge_type, scen_fuel_type)
    return adjusted_baseline + scaled_diff

s1_total = calc_scenario(s1_val)
s2_total = calc_scenario(s2_val)
s3_total = calc_scenario(s3_val)
s4_total = calc_scenario(s4_val)

# ==========================================
# 6. VISUALISATION
# ==========================================
st.divider()
st.markdown("### 📊 Scenario Impact Results")

# Output metrics
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("1. Adjusted Baseline", f"£{adjusted_baseline:,.2f}", help="Original Baseline + Your Global Interacting Allowances")
mc2.metric("2. Scenario 1 Total", f"£{s1_total:,.2f}", delta=f"£{s1_total - adjusted_baseline:,.2f}")
mc3.metric("3. Scenario 2 Total", f"£{s2_total:,.2f}", delta=f"£{s2_total - adjusted_baseline:,.2f}")
mc4.metric("4. Scenario 3 Total", f"£{s3_total:,.2f}", delta=f"£{s3_total - adjusted_baseline:,.2f}")
mc5.metric("5. Scenario 4 Total", f"£{s4_total:,.2f}", delta=f"£{s4_total - adjusted_baseline:,.2f}")

# Chart
fig = go.Figure()

x_labels = ['Adjusted Baseline', 'Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4']
y_vals = [adjusted_baseline, s1_total, s2_total, s3_total, s4_total]

# Highlight the Baseline in a different color
colors = ['#94a3b8', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b']

fig.add_trace(go.Bar(
    x=x_labels, 
    y=y_vals,
    marker_color=colors,
    text=[f"£{v:,.2f}" for v in y_vals],
    textposition='auto',
    hovertemplate="<b>%{x}</b><br>Total Bill: £%{y:.2f}<extra></extra>"
))

fig.update_layout(
    title="Total Annualised Bill Projection Across Scenarios",
    yaxis_title="Annualised Cost (£)",
    hovermode="x unified",
    showlegend=False,
    yaxis=dict(range=[min(y_vals)*0.95, max(y_vals)*1.02]) # Zooms in to make variances visually obvious
)

st.plotly_chart(fig, use_container_width=True)

# Clarification Box
if total_global_adj != 0:
    st.info(f"💡 **Note on Math:** The 'Adjusted Baseline' above includes your global interacting changes totaling **£{total_global_adj:,.2f}**. The Delta (red/green) beneath Scenarios 1-4 shows the isolated impact of your Scenario Variable.")
