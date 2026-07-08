import streamlit as st
import PyPDF2
import os
from datetime import datetime

# Import the local NLP summarization tools
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

# Ensure the local language tokenizer is downloaded (runs silently in the background)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

st.set_page_config(page_title="Local NLP Ofgem Timeline", layout="wide")

# 1. PDF Text Extraction Engine
def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            # Read just the first 5 pages where the Executive Summary usually lives
            num_pages = min(5, len(reader.pages))
            for i in range(num_pages):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        return ""

# 2. Local Mathematical Summarization Engine
@st.cache_data(show_spinner=False)
def generate_local_summary(pdf_path):
    """Uses a local LexRank algorithm to find the 4 most important sentences."""
    if not os.path.exists(pdf_path):
        return ["⚠️ PDF file not found in the local repository. Please check the file name."]
        
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        return ["⚠️ Could not extract readable text from this PDF."]
    
    try:
        # Feed the text to the NLP parser
        parser = PlaintextParser.from_string(raw_text, Tokenizer("english"))
        summarizer = LexRankSummarizer()
        
        # Ask the algorithm for the top 4 sentences
        summary_sentences = summarizer(parser.document, 4)
        
        # Clean up the output into a list of readable strings
        return [str(sentence).strip() for sentence in summary_sentences]
    
    except Exception as e:
        return [f"⚠️ Local summarization failed: {e}"]

# 3. The Repository Ledger (Updated for your exact naming convention)
# Publication dates are approximate based on standard Ofgem announcement schedules
REGULATORY_DOCS = [
    {
        "Cap_Period": "Jul 2026 - Sept 2026",
        "Publication_Date": datetime(2026, 5, 22),
        "File_Path": "pdfs/ofgem_cap_jul2026.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2026-06/Summary-of-changes-to-energy-price-cap-1-July-to-30-September-2026-revised-TDCV.pdf"
    },
    {
        "Cap_Period": "Apr 2026 - Jun 2026",
        "Publication_Date": datetime(2026, 2, 20),
        "File_Path": "pdfs/ofgem_cap_apr2026.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2026-02/Summary-of-changes-to-energy-price-cap-1-April-to-30-June-2026.pdf"
    },
    {
        "Cap_Period": "Jan 2026 - Mar 2026",
        "Publication_Date": datetime(2025, 11, 21),
        "File_Path": "pdfs/ofgem_cap_jan2026.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2025-11/Summary-of-changes-to-energy-price-cap-1-January-to-31-March-2026.pdf"
    },
    {
        "Cap_Period": "Oct 2025 - Dec 2025",
        "Publication_Date": datetime(2025, 8, 22),
        "File_Path": "pdfs/ofgem_cap_oct2025.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2025-08/summary-of-changes-to-energy-price-cap-1-october-to-31-december-2025.pdf"
    },
    {
        "Cap_Period": "Jul 2025 - Sept 2025",
        "Publication_Date": datetime(2025, 5, 23),
        "File_Path": "pdfs/ofgem_cap_jul2025.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2025-05/Summary%20of%20changes%20to%20energy%20price%20cap%201%20July%20to%2030%20September%202025_0.pdf"
    },
    {
        "Cap_Period": "Apr 2025 - Jun 2025",
        "Publication_Date": datetime(2025, 2, 21),
        "File_Path": "pdfs/ofgem_cap_apr2025.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2025-02/Summary-of-changes-to-energy-price-cap-1-April-to-30-June-2025_1.pdf"
    },
    {
        "Cap_Period": "Jan 2025 - Mar 2025",
        "Publication_Date": datetime(2024, 11, 22),
        "File_Path": "pdfs/ofgem_cap_jan2025.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2024-11/Summary_of_Changes_to_Energy_Price_Cap_1_January_to_31_March_2025.pdf"
    },
    {
        "Cap_Period": "Oct 2024 - Dec 2024",
        "Publication_Date": datetime(2024, 8, 23),
        "File_Path": "pdfs/ofgem_cap_oct2024.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2024-08/Summary_of_Changes_to_Energy_Price_Cap_1_October_to_31_December_2024.pdf"
    },
    {
        "Cap_Period": "Jul 2024 - Sept 2024",
        "Publication_Date": datetime(2024, 5, 24),
        "File_Path": "pdfs/ofgem_cap_jul2024.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2024-05/Summary%20of%20changes%20to%20energy%20price%20cap%201%20July%20to%2030%20September%202024.pdf"
    },
    {
        "Cap_Period": "Apr 2024 - Jun 2024",
        "Publication_Date": datetime(2024, 2, 23),
        "File_Path": "pdfs/ofgem_cap_apr2024.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2025-09/Default%20Tariff%20Cap%20Letter%20-%201%20April%202024%20.pdf"
    },
    {
        "Cap_Period": "Jan 2024 - Mar 2024",
        "Publication_Date": datetime(2023, 11, 23),
        "File_Path": "pdfs/ofgem_cap_jan2024.pdf",
        "PDF_Link": "https://www.ofgem.gov.uk/sites/default/files/2023-11/Default%20Tariff%20Cap%20Letter%20for%201%20January%202024.pdf"
    }
]

# Sort newest to top so the timeline flows downward from the present
REGULATORY_DOCS.sort(key=lambda x: x["Publication_Date"], reverse=True)

# 4. Build the UI
st.title("📑 NLP Regulatory Timeline")
st.write("Upload official Ofgem PDFs, and local algorithms will extract the core methodology changes automatically.")
st.markdown("---")

current_time = datetime.now()

# 5. Render the Timeline
for doc in REGULATORY_DOCS:
    pub_date = doc["Publication_Date"]
    
    # Automatically flag the active cap based on the current system date
    if pub_date.year == current_time.year and pub_date.month == current_time.month:
        badge = '<span style="background-color:#2ecc71; color:white; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:12px;">🟢 CURRENT CAP</span>'
    elif pub_date > current_time:
        badge = '<span style="background-color:#f1c40f; color:black; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:12px;">🟡 UPCOMING</span>'
    else:
        badge = '<span style="background-color:#95a5a6; color:white; padding:4px 8px; border-radius:4px; font-weight:bold; font-size:12px;">⚫ HISTORICAL</span>'

    col_date, col_line, col_content = st.columns([2, 0.5, 7])
    
    with col_date:
        st.write(f"### {pub_date.strftime('%d %b %Y')}")
        st.markdown(badge, unsafe_allow_html=True)
        
    with col_line:
        # Drawing the vertical timeline track
        st.markdown('<div style="border-left: 3px solid #34495e; height: 100%; min-height: 200px; margin-left: 20px; opacity: 0.6;"></div>', unsafe_allow_html=True)
        
    with col_content:
        st.markdown(f"## {doc['Cap_Period']}")
        
        # Fire the local NLP Extractor
        with st.spinner("NLP scanning document..."):
            extracted_points = generate_local_summary(doc["File_Path"])
            
        st.markdown("**Core Extraction:**")
        
        # Format the top 4 sentences as clean bullet points
        for point in extracted_points:
            st.write(f"- {point}")
            
        st.markdown(f"<br>[🔗 View Original Ofgem Document]({doc['PDF_Link']})", unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
