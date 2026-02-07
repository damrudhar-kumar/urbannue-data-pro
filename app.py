import streamlit as st
import pandas as pd
import google.generativeai as genai
from supabase import create_client, Client
import shopify
import requests
from urllib.parse import urlparse

# 1. Page Configuration
st.set_page_config(page_title="Urbannue Pro | Intelligence", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0E1117; color: white; }
    .stButton>button { 
        background-color: #D4AF37; color: black; font-weight: bold; border-radius: 8px; width: 100%;
    }
    .stTextInput>div>div>input { background-color: #161B22; color: white; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Supabase Connection
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

def save_token(shop, token):
    data = {"shop_url": shop, "access_token": token}
    supabase.table("shopify_sessions").upsert(data).execute()

def get_stored_token(shop_url):
    # Clean the URL to match stored format
    clean_url = shop_url.replace("https://", "").replace("http://", "").strip("/")
    response = supabase.table("shopify_sessions").select("access_token").eq("shop_url", clean_url).execute()
    return response.data[0]['access_token'] if response.data else None

# 3. Handle Shopify OAuth Callback (The Handshake)
query_params = st.query_params
if "code" in query_params and "shop" in query_params:
    shop = query_params["shop"]
    code = query_params["code"]
    
    # Clean the shop domain for the API call
    clean_shop = shop.replace("https://", "").replace("http://", "").strip("/")
    
    try:
        # Step 4: Exchange code for permanent token
        token_url = f"https://{clean_shop}/admin/oauth/access_token"
        payload = {
            "client_id": st.secrets["SHOPIFY_API_KEY"], 
            "client_secret": st.secrets["SHOPIFY_API_SECRET"], 
            "code": code
        }
        
        # Use a real POST request to get the token
        res = requests.post(token_url, json=payload, timeout=15)
        res_data = res.json()
        
        access_token = res_data.get("access_token")
        
        if access_token:
            save_token(clean_shop, access_token)
            st.session_state["token"] = access_token
            st.session_state["authenticated"] = True
            st.query_params.clear()
            st.success("Token secured! Reloading...")
            st.rerun()
        else:
            st.error(f"Failed to get token: {res_data.get('errors')}")
            
    except Exception as e:
        st.error(f"Handshake Network Error: {e}")

# 4. Access Security
if "authenticated" not in st.session_state:
    st.title("🔒 Urbannue Pro Login")
    col1, _ = st.columns([1, 2])
    with col1:
        pwd = st.text_input("Enter Access Code", type="password")
        if st.button("Unlock Dashboard"):
            if pwd == st.secrets["ACCESS_PASSWORD"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid Code.")
    st.stop()

# 5. Dashboard Layout
st.title("🏆 Urbannue Pro | Business Intelligence")

with st.sidebar:
    st.header("Store Status")
    raw_url = st.text_input("Enter Store URL", placeholder="brand.myshopify.com")
    # Auto-clean input
    shop_input = raw_url.replace("https://", "").replace("http://", "").strip("/")
    
    if shop_input:
        token = get_stored_token(shop_input)
        
        if token:
            st.success("✅ Connected")
            st.session_state["token"] = token
            if st.button("Reset / Update Permissions"):
                if "token" in st.session_state:
                    del st.session_state["token"]
                st.rerun()
        else:
            st.warning("⚠️ Auth Needed")
            if st.button("Connect to Shopify"):
                api_key = st.secrets["SHOPIFY_API_KEY"]
                scopes = "read_orders,read_products,read_customers"
                redirect_uri = "https://urbannue-data-pro-n9nzm7h4zeyxuvkqt5lmys.streamlit.app" 
                install_url = f"https://{shop_input}/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}"
                st.markdown(f"**[Click here to Authorize Urbannue]({install_url})**")

# 6. Analysis Engine
# 6. Analysis Engine
st.divider()

if "token" in st.session_state:
    # --- CRITICAL URL CLEANING START ---
    # This removes https://, slashes, and spaces to prevent Errno -2
    clean_domain = shop_input.replace("https://", "").replace("http://", "").strip().split('/')[0]
    # --- CRITICAL URL CLEANING END ---

    st.subheader(f"Analyzing: {clean_domain}")
    
    try:
        # Initialize Shopify Session with the CLEAN domain
        session = shopify.Session(clean_domain, "2024-04", st.session_state["token"])
        shopify.ShopifyResource.activate_session(session)
        
        # Fetch Orders (using 'any' status to catch your fake orders)
        orders = shopify.Order.find(limit=50, status="any")
        shopify.ShopifyResource.clear_session()
        
        if orders:
            order_list = []
            for o in orders:
                order_list.append({
                    "ID": o.name, 
                    "Total": float(o.total_price), 
                    "Date": o.created_at,
                    "Status": o.financial_status
                })
            df = pd.DataFrame(order_list)

            # Dashboard Visuals
            m1, m2, m3 = st.columns(3)
            m1.metric("Orders", len(df))
            m2.metric("Revenue", f"₹{df['Total'].sum():,.2f}")
            m3.metric("AOV", f"₹{df['Total'].mean():,.2f}")

            st.write("### 📦 Live Store Data")
            st.dataframe(df, use_container_width=True)

            # AI Logic
            query = st.chat_input("Ask about your sales...")
            if query:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-3-flash-preview')
                with st.status("AI Analyzing Data..."):
                    context = f"Store: {clean_domain}. Data: {df.to_json(orient='records')}"
                    response = model.generate_content(f"{context}\n\nUser Question: {query}")
                    st.markdown(response.text)
        else:
            st.info(f"Connected to {clean_domain}, but no orders were found. Check if your test orders are archived.")
            
    except Exception as e:
        if "403" in str(e):
            st.error("🚨 Permission Denied. Use the 'Reset' button in the sidebar to update permissions.")
        else:
            # This will now show exactly what domain it failed on
            st.error(f"Analysis Error on {clean_domain}: {e}")
