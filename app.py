import streamlit as st
import pandas as pd
import google.generativeai as genai
from supabase import create_client, Client
import shopify
import requests

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
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

def save_token(shop, token):
    data = {"shop_url": shop, "access_token": token}
    supabase.table("shopify_sessions").upsert(data).execute()

def get_stored_token(shop_url):
    response = supabase.table("shopify_sessions").select("access_token").eq("shop_url", shop_url).execute()
    return response.data[0]['access_token'] if response.data else None

# 3. Handle Shopify Callback (The "Digital Handshake")
# This runs BEFORE the password screen to prevent the loop
query_params = st.query_params
if "code" in query_params and "shop" in query_params:
    shop = query_params["shop"]
    code = query_params["code"]
    
    # Exchange code for permanent access token
    try:
        api_key = st.secrets["SHOPIFY_API_KEY"]
        api_secret = st.secrets["SHOPIFY_API_SECRET"]
        
        # Request permanent token
        conn = requests.post(
            f"https://{shop}/admin/oauth/access_token",
            json={"client_id": api_key, "client_secret": api_secret, "code": code}
        )
        access_token = conn.json().get("access_token")
        
        if access_token:
            save_token(shop, access_token)
            st.session_state["token"] = access_token
            st.session_state["authenticated"] = True
            st.success("Successfully connected to Shopify!")
            st.query_params.clear() # Clean URL
            st.rerun()
    except Exception as e:
        st.error(f"Auth failed: {e}")

# 4. Access Security Screen
if "authenticated" not in st.session_state:
    st.title("🔒 Urbannue Pro Login")
    col1, _ = st.columns([1, 2])
    with col1:
        pwd = st.text_input("Enter your Private Access Code", type="password")
        if st.button("Unlock Dashboard"):
            if pwd == st.secrets["ACCESS_PASSWORD"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid Code.")
    st.stop()

# 5. Main Product Layout
st.title("🏆 Urbannue Pro | Business Intelligence")

with st.sidebar:
    st.header("Store Status")
    shop_input = st.text_input("Enter Store URL", placeholder="your-brand.myshopify.com")
    
    if shop_input:
        token = get_stored_token(shop_input)
        if token:
            st.success("✅ Store Connected")
            st.session_state["token"] = token
        else:
            st.warning("⚠️ Not connected.")
            if st.button("Connect to Shopify"):
                api_key = st.secrets["SHOPIFY_API_KEY"]
                redirect_uri = "https://urbannue-data-pro-n9nzm7h4zeyxuvkqt5lmys.streamlit.app" 
                install_url = f"https://{shop_input}/admin/oauth/authorize?client_id={api_key}&scope=read_orders,read_products&redirect_uri={redirect_uri}"
                st.markdown(f"**[Authorize Urbannue Now]({install_url})**")

# 6. AI Consultant Interface
st.divider()

if "token" in st.session_state:
    st.subheader(f"Analyzing: {shop_input}")
    
    # KPIs (Example View)
    k1, k2, k3 = st.columns(3)
    k1.metric("Live Orders", "1,240", "Optimal")
    k2.metric("Revenue", "₹4,52,000", "+8%")
    k3.metric("AI Confidence", "98%")

    query = st.chat_input("Ask about your sales trends...")

    if query:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        with st.status("Consulting Engine...", expanded=True):
            full_prompt = f"Shopify Store {shop_input}. Request: {query}. Output professional analyst insights."
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
else:
    st.info("Enter your store URL in the sidebar to begin.")
