import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Ofgem Price Cap Dashboard", layout="wide", page_icon="⚡")
st.title("⚡ Ofgem Energy Price Cap Visualizer")
st.markdown("Explore how wholesale, policy, network, and operating costs have evolved over time.")

# ==========================================
# 2. DICTIONARIES & METADATA
# ==========================================
ALLOWANCE_DICT = {
    'DF': 'Direct Fuel Cost',
    'CM': 'Capacity Market',
    'AA': 'Adjustment Allowance',
    'PC': 'Policy Costs',
    'NC': 'Network Costs',
    'OC': 'Operating Costs (Legacy)',
    'CO': 'Core Operating Costs',
    'SMNCC': 'Smart Metering Net Cost Change',
    'IC': 'Industry Charges',
    'PAAC': 'Payment Method Uplift (Fixed)',
    'PAP': 'Payment Method Uplift (Variable)',
    'DRC': 'Debt-Related Costs',
    'EBIT': 'Earnings Before Interest and Tax',
    'HAP': 'Headroom Allowance Percentage',
    'RO': 'Renewables Obligation (RO)',
    'FiT': 'Feed-in Tariff (FiT)',
    'ECO': 'Energy Company Obligation (ECO)',
    'WHD': 'Warm Home Discount (WHD)',
    'WHD (unit rate)': 'Warm Home Discount (Unit Rate)',
    'AAHEDC': 'Assistance for Areas with High Electricity Distribution Costs',
    'NCC': 'Network Charging Compensation',
    'nRAB': 'Nuclear Regulated Asset Base',
    'CfD': 'Contracts for Difference (CfD)',
    'Backwardation': 'Backwardation',
    'Gas Transmission': 'Gas Transmission',
    'Gas Distribution': 'Gas Distribution',
    'TNUoS': 'Transmission Network Use of System (TNUoS)',
    'BSUoS': 'Balancing Services Use of System (BSUoS)',
    'DUoS': 'Distribution Use of System (DUoS)'
}

POLICY_EVENTS = {
    "2022-06-23": "Updated CfD methodology (dynamic negative recovery)",
    "2022-08-04": "Wholesale Cost Adjustment (+£46 for SVT demand)",
    "2023-02-17": "COVID-19 True-Up Process (+£11 for bad debt)",
    "2023-02-27": "ECO+ / GBIS allowance introduced",
    "2023-08-25": "EBIT hybrid model (+£10) & ASC Bad Debt (+£8.77)",
    "2024-02-23": "Debt Float (+£28) & Standing Charge Levelisation",
    "2024-08-23": "ASC Bad Debt Allowance extended",
    "2025-02-25": "Network Charging Compensation (NCC) (+£3)",
    "2025-05-23": "Enduring OPEX framework replaces debt floats (-£8 avg)",
    "2025-08-25": "Interim UIG Allowance updated (+£4.30)",
    "2025-10-24": "WHD Scheme Expansion Cost (+£7)",
    "2025-11-21": "nRAB Allowance (+£14), GCF adjustment, Deadband removed",
    "2025-12-09": "WHD shifted from standing charge to unit rate"
}

# ==========================================
# 3. DATA LOADING (Cached for speed)
# ==========================================
@st.cache_data
def load_data(filename):
    try:
        df = pd.read_csv(filename)
        # Ensure Start Date is a datetime object for plotting timelines
        if 'Start Date' in df.columns:
            df['Start Date'] = pd.to_datetime(df['Start Date'])
        # Translate allowances using the dictionary
        if 'Allowance' in df.columns:
            df['Allowance_Full'] = df['Allowance'].map(ALLOWANCE_DICT).fillna(df['Allowance'])
        return df
    except Exception as e:
        return pd.DataFrame() # Return empty df if file is missing

df_opex = load_data('Cleaned_Price_Cap_Data.csv')
df_whole = load_data('wholesale_allowances_cleaned.csv')
df_policy = load_data('policy_costs_cleaned.csv')
df_net = load_data('network_costs_cleaned.csv')
df_bench = load_data('total_bill_cleaned.csv')

# ==========================================
# 4. GLOBAL SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("Global Filters")

# We use Opex as the master list of periods/fuels since it's the most comprehensive
fuel_types = ["Electricity Single-Rate", "Electricity Multi-Register", "Gas", "Dual Fuel (implied)"]
payment_methods = ["Direct Debit", "Standard Credit", "PPM"]
charge_types = ["Standing Charge", "Unit Rate"]

selected_fuel = st.sidebar.selectbox("Fuel Type", options=fuel_types)
selected_payment = st.sidebar.selectbox("Payment Method", options=payment_methods)
selected_charge = st.sidebar.selectbox("Charge Type", options=charge_types)

st.sidebar.divider()
st.sidebar.header("Benchmark Overlay")
selected_benchmark = st.sidebar.selectbox(
    "Compare trendline against:", 
    options=["None", "Total SC", "Total UR", "Total Bill"]
)

# ==========================================
# 5. HELPER FUNCTION: RENDER TABS
# ==========================================
def render_tab_content(dataset, tab_title):
    if dataset.empty:
        st.warning(f"No data found for {tab_title}. Please ensure the CSV is uploaded.")
        return

    # Filter data by sidebar selections
    # Note: Network/Wholesale/Policy might not have Payment Method split, handle gracefully
    filtered = dataset[(dataset['Fuel Type'].str.contains(selected_fuel.split()[0], na=False, case=False)) & 
                       (dataset['Charge Type'] == selected_charge)]
    
    if 'Payment Method' in filtered.columns and not filtered[filtered['Payment Method'] == selected_payment].empty:
        filtered = filtered[filtered['Payment Method'] == selected_payment]

    if filtered.empty:
        st.info(f"No {tab_title} data available for the selected combination.")
        return

    # --- UI: Allowance Selector ---
    available_allowances = filtered['Allowance_Full'].unique()
    selected_allowances = st.multiselect(
        f"Select {tab_title} Allowances to view:", 
        options=available_allowances, 
        default=available_allowances[:3] if len(available_allowances) >= 3 else available_allowances
    )
    
    chart_data = filtered[filtered['Allowance_Full'].isin(selected_allowances)]
    
    if chart_data.empty:
        return

    # --- UI: Time Slider for Snapshot Bar Chart ---
    cap_periods = sorted(chart_data['Start Date'].unique())
    period_labels = chart_data[['Start Date', 'Cap Period']].drop_duplicates().sort_values('Start Date')
    
    st.markdown("### Snapshot in Time")
    selected_date = st.select_slider(
        "Select Cap Period:",
        options=period_labels['Start Date'],
        format_func=lambda x: period_labels[period_labels['Start Date'] == x]['Cap Period'].values[0]
    )
    
    snapshot_data = chart_data[chart_data['Start Date'] == selected_date]
    
    # Snapshot Bar Chart
    fig_bar = px.bar(
        snapshot_data, x='Allowance_Full', y='Cost Value', color='Allowance_Full',
        title=f"{tab_title} Breakdown for Selected Period (£)",
        text_auto='.2f'
    )
    fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Cost Value (£)")
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- UI: Trend Over Time Toggle ---
    st.divider()
    show_trend = st.toggle(f"📈 Show {tab_title} trend over time", value=False)
    
    if show_trend:
        st.markdown("### Historical Trend & Policy Events")
        
        # Base Line Chart
        fig_line = px.line(
            chart_data, x='Start Date', y='Cost Value', color='Allowance_Full', markers=True,
            title="Allowance Changes Over Time"
        )
        
        # Add Benchmark Overlay if selected
        if selected_benchmark != "None" and not df_bench.empty:
            bench_data = df_bench[(df_bench['Fuel Type'].str.contains(selected_fuel.split()[0], na=False, case=False)) & 
                                  (df_bench['Payment Method'] == selected_payment) & 
                                  (df_bench['Charge Type'] == selected_benchmark)]
            if not bench_data.empty:
                bench_data = bench_data.sort_values('Start Date')
                fig_line.add_trace(go.Scatter(
                    x=bench_data['Start Date'], y=bench_data['Cost Value'],
                    mode='lines+markers', name=selected_benchmark,
                    line=dict(color='black', width=3, dash='dash')
                ))

        # Add Policy Event Annotations
        show_events = st.checkbox("Show Policy Events Overlay", value=True)
        if show_events:
            for date_str, event_text in POLICY_EVENTS.items():
                event_date = pd.to_datetime(date_str)
                # Only show events that fall within our dataset's timeframe
                if event_date >= chart_data['Start Date'].min() and event_date <= chart_data['Start Date'].max():
                    fig_line.add_vline(
                        x=event_date, line_width=1, line_dash="dot", line_color="red",
                        annotation_text="ℹ️", annotation_position="top right",
                        annotation_hovertext=f"{date_str}: {event_text}"
                    )
        
        fig_line.update_layout(xaxis_title="Cap Period", yaxis_title="Cost Value (£)", hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# 6. MAIN APP: TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["🏭 Wholesale", "📜 Policy", "🔌 Network", "🏢 OPEX"])

with tab1:
    render_tab_content(df_whole, "Wholesale")
with tab2:
    render_tab_content(df_policy, "Policy")
with tab3:
    render_tab_content(df_net, "Network")
with tab4:
    render_tab_content(df_opex, "OPEX")
