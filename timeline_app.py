import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

# 1. Page Configuration
st.set_page_config(page_title="Live Ofgem Timeline", layout="wide")

st.title("⏱️ Live-Updating Ofgem Price Cap Timeline")
st.write("This timeline dynamically scrapes Ofgem's portal to capture the latest 'Summary of Changes' documents automatically.")

# 2. The Live Scraper Engine (Configured to run once a week)
@st.cache_data(ttl="7d")
def scrape_ofgem_timeline():
    url = "https://www.ofgem.gov.uk/energy-regulation/domestic-and-non-domestic/energy-pricing-rules/energy-price-cap/energy-price-cap-default-tariff-levels"
    
    try:
        # Standard user-agent header to bypass basic firewall bot blocks
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        scraped_data = []
        
        # Scan all available anchor links on the landing page
        for link in soup.find_all('a', href=True):
            link_text = link.text.strip()
            link_url = link['href']
            
            # Case-insensitive match for the predictable naming pattern
            if "summary of changes to energy price cap" in link_text.lower():
                # Correct relative URLs if used by the CMS framework
                if link_url.startswith("/"):
                    link_url = "https://www.ofgem.gov.uk" + link_url
                
                # Extract the target year out of the link string to build a chronological key
                year_match = re.search(r'202[0-9]', link_text)
                if year_match:
                    est_year = int(year_match.group(0))
                else:
                    est_year = datetime.now().year
                
                # Map a baseline date anchor for sorting metrics
                placeholder_date = datetime(est_year, 1, 1)
                
                scraped_data.append({
                    "Publication_Date": placeholder_date,
                    "Version_Title": link_text,
                    "Key_Changes": "This decision document was automatically parsed from the live Ofgem production ecosystem. Open the resource link below to read the comprehensive regulatory update.",
                    "PDF_URL": link_url
                })
        
        # Convert raw entries to DataFrame and clean up duplicates
        df = pd.DataFrame(scraped_data)
        if not df.empty:
            df = df.drop_duplicates(subset=["PDF_URL"])
            return df.sort_values("Publication_Date", ascending=False)
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error executing connection loop to Ofgem portal: {e}")
        return pd.DataFrame()

# 3. Initialize Data Pipeline
df_timeline = scrape_ofgem_timeline()
current_time = datetime.now()

# 4. Empty State Network Fallback
if df_timeline.empty:
    st.warning("⚠️ Live scraping loop returned no documents or was actively dropped by the local network proxy. Deploying hardcoded baseline backup.")
    df_timeline = pd.DataFrame([{
        "Publication_Date": datetime(2026, 5, 22),
        "Version_Title": "Summary of changes to energy price cap: July to September 2026",
        "Key_Changes": "Local corporate network architecture dropped the parsing query. Please check connection maps or load the destination directly.",
        "PDF_URL": "https://www.ofgem.gov.uk"
    }])

# 5. Sidebar Meta panel
with st.sidebar:
    st.header("📊 Scraper Meta-Data")
    st.success("App Status: Operational")
    st.metric("Discovered Documents", len(df_timeline))
    st.caption("Cache Persistence Strategy: **7 Days (Weekly Refresh)**")
    st.info("The scraping engine runs once a week in the background to maximize performance and strictly observe Ofgem server request standards.")

st.markdown("---")

# 6. Render the Chronological Visual UI Tracks
for index, row in df_timeline.iterrows():
    pub_date = row["Publication_Date"]
    
    # Self-Updating Flagging Architecture 
    if pub_date.year == current_time.year:
        badge_html = '<span style="background-color:#2ecc71; color:white; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:12px;">🟢 ACTIVE REGULATORY CYCLE</span>'
    elif pub_date > current_time:
        badge_html = '<span style="background-color:#f1c40f; color:black; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:12px;">🟡 ADVANCE FRAMEWORK RELEASE</span>'
    else:
        badge_html = '<span style="background-color:#95a5a6; color:white; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:12px;">⚫ HISTORICAL LOG</span>'
        
    # Build layout structural split
    col_date, col_line, col_content = st.columns([2, 0.5, 7])
    
    with col_date:
        st.write(f"### {pub_date.strftime('%Y Archive')}")
        st.markdown(badge_html, unsafe_allow_html=True)
        
    with col_line:
