import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Price Cap Sandbox", layout="wide", page_icon="🎛️")
st.title("🎛️ Energy Price Cap Simulator & Sandbox")
st.markdown("Play with the July 2026 price cap allowances. Add, edit, or remove policies to simulate the exact impact on the final consumer bill.")

# ==========================================
# 2. LOAD DATA & TDCV METADATA
# ==========================================
@st.cache_data
def load_sandbox_data():
    try:
        df = pd.read_csv("sandbox/Sandbox_Master_Allowances_July2026.csv")
        return df
    except FileNotFoundError:
        st.error("Missing 'Sandbox_Master_Allowances_July2026.csv'. Please run the Colab extraction script first.")
        return pd.DataFrame()

df_master = load_sandbox_data()

# Official Ofgem TDCV values (July 2026 onwards)
TDCV_DEFAULTS = {
    'Gas': 11500,
    'Electricity Single-Rate': 2900,
    'Electricity Multi-Register': 3900,
    'Dual Fuel (implied)': 100 
}

# ==========================================
# 3. SIDEBAR ENGINE: ANCHORS & CONSUMPTION
# ==========================================
st.sidebar.header("1. Choose Baseline Profile")

if not df_master.empty:
    available_fuels = sorted([str(x) for x in df_master['Fuel Type'].dropna().unique()])
    available_pms = sorted([str(x) for x in df_master['Payment Method'].dropna().unique()])
else:
    available_fuels, available_pms = [], []

selected_fuel = st.sidebar.selectbox("Fuel Type", options=available_fuels)
selected_pm = st.sidebar.selectbox("Payment Method", options=available_pms)

st.sidebar.divider()
st.sidebar.header("2. Set Consumer Usage")

use_tdcv = st.sidebar.checkbox("Use Standard Ofgem TDCV", value=True)

# Smart Logic for Dual Fuel vs Single Fuel
if selected_fuel == 'Dual Fuel (implied)':
    st.sidebar.markdown("*Dual Fuel scaling options:*")
    scale_mode = st.sidebar.radio("Scaling Method", ["Percentage Increase", "Custom Gas & Elec kWh"])
    
    if scale_mode == "Percentage Increase":
        custom_usage = st.sidebar.number_input(
            "Usage Level (%)", 
            min_value=10, max_value=300, value=100, step=10,
            disabled=use_tdcv
        )
        usage_multiplier_gas = custom_usage / 100.0
        usage_multiplier_elec = custom_usage / 100.0
    else:
        gas_usage = st.sidebar.number_input("Gas Consumption (kWh)", value=11500, step=100, disabled=use_tdcv)
        elec_usage = st.sidebar.number_input("Elec Consumption (kWh)", value=2900, step=100, disabled=use_tdcv)
        usage_multiplier_gas = gas_usage / 11500.0
        usage_multiplier_elec = elec_usage / 2900.0
else:
    default_tdcv = TDCV_DEFAULTS.get(selected_fuel, 2900)
    custom_usage = st.sidebar.number_input(
        f"Annual Consumption (kWh)", 
        min_value=0, value=default_tdcv, step=100,
        disabled=use_tdcv
    )
    usage_multiplier_single = custom_usage / default_tdcv

st.sidebar.divider()
st.sidebar.info("💡 **How scaling works:** Standing Charge changes apply a flat £ impact. Unit Rate changes scale dynamically based on the consumption entered above.")

# ==========================================
# 4. INITIALIZE SESSION STATE FOR CUSTOM POLICIES
# ==========================================
if 'custom_policies' not in st.session_state:
    st.session_state.custom_policies = []

# ==========================================
# 5. MAIN SANDBOX LAYOUT
# ==========================================
if df_master.empty:
    st.stop()

# Secretly split Dual Fuel into its pure components to allow independent SC/UR math
if selected_fuel == 'Dual Fuel (implied)':
    df_filtered = df_master[(df_master['Fuel Type'].isin(['Gas', 'Electricity Single-Rate'])) & 
                            (df_master['Payment Method'] == selected_pm)].copy()
    # Add labels so the user knows which fuel they are tweaking
    df_filtered['Allowance'] = df_filtered['Allowance'] + " (" + df_filtered['Fuel Type'].replace({'Electricity Single-Rate': 'Elec'}) + ")"
else:
    df_filtered = df_master[(df_master['Fuel Type'] == selected_fuel) & 
                            (df_master['Payment Method'] == selected_pm)].copy()

if df_filtered.empty:
    st.warning("No baseline data available for this specific combination.")
    st.stop()

col_controls, col_visuals = st.columns([1.2, 2])

simulated_values = {}

with col_controls:
    st.subheader("🛠️ Policy Control Panel")
    st.markdown("*(Values shown are annualized £ at standard TDCV)*")
    
    categories = sorted(df_filtered['Tab Category'].unique())
    
    for category in categories:
        with st.expander(f"📁 {category}", expanded=False):
            cat_data = df_filtered[df_filtered['Tab Category'] == category]
            
            # We now grab 'idx' (the unique row number) to ensure perfect key uniqueness
            for idx, row in cat_data.iterrows():
                allowance_name = row['Allowance']
                charge_type = row['Charge Type']
                fuel_type_row = row['Fuel Type']
                base_val = float(row['Allowance Value'])
                
                # Inject 'idx' into the key so it is 100% unique, even if names match
                widget_key = f"{category}_{allowance_name}_{charge_type}_{idx}"
                
                sim_val = st.number_input(
                    label=f"{allowance_name} ({'SC' if charge_type == 'Standing Charge' else 'UR'})",
                    value=base_val,
                    step=5.0,
                    key=widget_key
                )
                
                simulated_values[widget_key] = {
                    'name': allowance_name,
                    'charge_type': charge_type,
                    'fuel_type': fuel_type_row,
                    'baseline': base_val,
                    'simulated': sim_val
                }

    # --- CUSTOM POLICY ADDER ---
    with st.expander("➕ Add Proposed Custom Policy", expanded=True):
        st.markdown("Introduce a brand new allowance to the price cap.")
        cp_name = st.text_input("Policy Name", placeholder="e.g., Green Grid Levy")
        cp_type = st.selectbox("Charge Application", ["Standing Charge", "Unit Rate"])
        cp_val = st.number_input("Annual Value at TDCV (£)", value=0.0, step=5.0)
        
        if st.button("Add Policy to Simulation"):
            if cp_name:
                st.session_state.custom_policies.append({
                    'name': cp_name,
                    'charge_type': cp_type,
                    'baseline': 0.0,
                    'simulated': cp_val
                })
                st.rerun()

    if st.session_state.custom_policies:
        if st.button("🗑️ Clear Custom Policies"):
            st.session_state.custom_policies = []
            st.rerun()
# ==========================================
# 6. CALCULATE IMPACTS & RENDER VISUALS
# ==========================================
with col_visuals:
    base_sc = 0.0; base_ur = 0.0
    sim_sc = 0.0; sim_ur = 0.0
    waterfall_steps = []
    
    # Process existing allowances
    for key, data in simulated_values.items():
        if data['charge_type'] == 'Standing Charge':
            mult = 1.0
        else:
            if selected_fuel == 'Dual Fuel (implied)':
                mult = usage_multiplier_gas if data['fuel_type'] == 'Gas' else usage_multiplier_elec
            else:
                mult = usage_multiplier_single
                
        adj_base = data['baseline'] * mult
        adj_sim = data['simulated'] * mult
        delta = adj_sim - adj_base
        
        if data['charge_type'] == 'Standing Charge':
            base_sc += adj_base; sim_sc += adj_sim
        else:
            base_ur += adj_base; sim_ur += adj_sim
        
        if round(delta, 2) != 0:
            waterfall_steps.append({'name': data['name'], 'delta': delta})
            
    # Process custom policies
    for cp in st.session_state.custom_policies:
        if cp['charge_type'] == 'Standing Charge':
            mult = 1.0
        else:
            mult = usage_multiplier_elec if selected_fuel == 'Dual Fuel (implied)' else usage_multiplier_single
            
        adj_sim = cp['simulated'] * mult
        
        if cp['charge_type'] == 'Standing Charge':
            sim_sc += adj_sim
        else:
            sim_ur += adj_sim
            
        if round(adj_sim, 2) != 0:
            waterfall_steps.append({'name': f"⭐ {cp['name']}", 'delta': adj_sim})

    total_baseline_bill = base_sc + base_ur
    total_simulated_bill = sim_sc + sim_ur
    net_impact = total_simulated_bill - total_baseline_bill

    # --- RENDER KPIs ---
    st.subheader("📊 Simulation Results")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Baseline Bill (July 2026)", f"£{total_baseline_bill:,.2f}")
    kpi2.metric("Simulated Bill", f"£{total_simulated_bill:,.2f}", delta=f"£{net_impact:,.2f}", delta_color="inverse")
    impact_pct = (net_impact / total_baseline_bill * 100) if total_baseline_bill > 0 else 0
    kpi3.metric("Percentage Change", f"{impact_pct:,.2f}%", delta=f"{impact_pct:,.2f}%", delta_color="inverse")
    st.divider()

    # --- GRAPH 1: STACKED BAR CHART (UR/SC SEPARATED) ---
    fig_bar = go.Figure(data=[
        go.Bar(name='Standing Charge', x=['Baseline', 'Simulated'], y=[base_sc, sim_sc], marker_color=['#aec7e8', '#c5b0d5']),
        go.Bar(name='Unit Rate', x=['Baseline', 'Simulated'], y=[base_ur, sim_ur], marker_color=['#1f77b4', '#9467bd'])
    ])
    fig_bar.update_layout(
        barmode='stack',
        title="Bill Breakdown: Standing Charge vs Unit Rate",
        yaxis_title="Annual Bill (£)",
        margin=dict(t=40, b=30),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- GRAPH 2: WATERFALL CHART (COLOR CODED) ---
    x_labels = ["Baseline Bill"]
    y_values = [total_baseline_bill]
    measure = ["absolute"]
    
    for step in waterfall_steps:
        x_labels.append(step['name'])
        y_values.append(step['delta'])
        measure.append("relative")
        
    if not waterfall_steps:
        x_labels.append("No Changes")
        y_values.append(0)
        measure.append("relative")
        
    x_labels.append("Simulated Bill")
    y_values.append(total_simulated_bill)
    measure.append("total")
    
    # Custom color mapping for exactly what you asked for
    wf_colors = []
    for i, m in enumerate(measure):
        if i == 0:
            wf_colors.append('#1f77b4') # Blue for Baseline Total
        elif i == len(measure) - 1:
            wf_colors.append('#9467bd') # Purple for Simulated Total
        else:
            wf_colors.append('#2ca02c' if y_values[i] < 0 else '#d62728') # Green/Red for Deltas

    fig_wf = go.Figure(go.Waterfall(
        name = "Impact", 
        orientation = "v",
        measure = measure,
        x = x_labels,
        textposition = "outside",
        text = [f"{'+' if v > 0 and m == 'relative' else ''}£{v:,.0f}" for v, m in zip(y_values, measure)],
        y = y_values,
        connector = {"line":{"color":"rgb(63, 63, 63)", "width": 2}},
        marker = dict(color=wf_colors)
    ))
    fig_wf.update_layout(
        title="Policy Impact Journey (Deltas)",
        waterfallgap=0.3,
        height=500,
        margin=dict(t=40, b=100),
        yaxis_title="Total Bill (£)"
    )
    st.plotly_chart(fig_wf, use_container_width=True)
