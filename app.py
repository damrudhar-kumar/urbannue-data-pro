import streamlit as st
import pandas as pd
import google.generativeai as genai
from supabase import create_client, Client
import shopify

# 1. Page Configuration & Premium Styling
st.set_page_config(page_title="Urbannue Pro | Intelligence", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0E1117; color: white; }
    .stButton>button { 
        background-color: #D4AF37; 
        color: black; 
        font-weight: bold;
        border-radius: 8px;
        width: 100%;
    }
    .stTextInput>div>div>input { background-color: #161B22; color: white; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Secure Connection to Supabase Vault
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

def get_stored_token(shop_url):
    response = supabase.table("shopify_sessions").select("access_token").eq("shop_url", shop_url).execute()
    return response.data[0]['access_token'] if response.data else None

# 3. Access Security Screen
if "authenticated" not in st.session_state:
    st.title("🔒 Urbannue Pro Login")
    col1, col2 = st.columns([1, 2])
    with col1:
        pwd = st.text_input("Enter your Private Access Code", type="password")
        if st.button("Unlock Dashboard"):
            if pwd == st.secrets["ACCESS_PASSWORD"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid Code. Please contact Urbannue Support.")
    st.stop()

# 4. Main Product Layout
st.title("🏆 Urbannue Pro | Business Intelligence")

with st.sidebar:
    st.header("Store Status")
    shop_url = st.text_input("Enter Store URL", placeholder="your-brand.myshopify.com")
    
    if shop_url:
        token = get_stored_token(shop_url)
        if token:
            st.success("✅ Store Connected via Vault")
            st.session_state["token"] = token
        else:
            st.warning("⚠️ Store not connected.")
            if st.button("Connect to Shopify"):
                api_key = st.secrets["SHOPIFY_API_KEY"]
                # Replace the URL below with your actual deployed Streamlit URL
                redirect_uri = "https://urbannue-data-pro-n9nzm7h4zeyxuvkqt5lmys.streamlit.app" 
                install_url = f"https://{shop_url}/admin/oauth/authorize?client_id={api_key}&scope=read_orders,read_products&redirect_uri={redirect_uri}"
                st.markdown(f"[Click here to authorize Urbannue]({install_url})")

# 5. The AI Consultant Interface
st.divider()

if "token" in st.session_state:
    st.subheader(f"Analyzing: {shop_url}")
    
    # KPIs (Mock data for now - will be replaced by API calls)
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Live Orders", "1,240", "+12%")
    kpi2.metric("Revenue (MTD)", "₹4,52,000", "+8%")
    kpi3.metric("AI Confidence", "98%", "Optimal")

    query = st.chat_input("Ask your business consultant about your sales trends...")

    if query:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        with st.status("Consulting AI Engine...", expanded=True) as status:
            st.write("Fetching Shopify order data...")
            st.write("Applying Business Analyst logic...")
            
            # System prompt to ensure premium insights
            full_prompt = f"Context: Shopify Store {shop_url}. Task: {query}. Output professional BA insights with charts."
            response = model.generate_content(full_prompt)
            
            st.markdown(response.text)
            status.update(label="Analysis Complete!", state="complete", expanded=False)
else:
    st.info("Please enter your store URL in the sidebar to begin the analysis.")
