import streamlit as st
import pandas as pd
import google.generativeai as genai
from supabase import create_client, Client
import shopify
import requests

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
    response = supabase.table("shopify_sessions").select("access_token").eq("shop_url", shop_url).execute()
    return response.data[0]['access_token'] if response.data else None

# 3. Shopify OAuth Callback Logic
query_params = st.query_params
if "code" in query_params and "shop" in query_params:
    shop = query_params["shop"]
    code = query_params["code"]
    try:
        conn = requests.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": st.secrets["SHOPIFY_API_KEY"], 
                "client_secret": st.secrets["SHOPIFY_API_SECRET"], 
                "code": code
            }
        )
        access_token = conn.json().get("access_token")
        if access_token:
            save_token(shop, access_token)
            st.session_state["token"] = access_token
            st.session_state["authenticated"] = True
            st.query_params.clear()
            st.rerun()
    except Exception as e:
        st.error(f"Auth failed: {e}")

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

# 5. Dashboard Layout & Sidebar
st.title("🏆 Urbannue Pro | Business Intelligence")

with st.sidebar:
    st.header("Store Status")
    shop_input = st.text_input("Enter Store URL", placeholder="brand.myshopify.com")
    
    if shop_input:
        token = get_stored_token(shop_input)
        
        # Scenario: Token exists but permission might be old/missing
        if token:
            st.success("✅ Store Linked")
            st.session_state["token"] = token
            
            st.write("---")
            st.write("💡 **Fixing 'Permission Denied'?**")
            if st.button("Reset & Re-authorize"):
                # Clear the token from session so the "Connect" button reappears
                if "token" in st.session_state:
                    del st.session_state["token"]
                st.rerun()
        
        # Scenario: No token (or just clicked Reset)
        if "token" not in st.session_state:
            st.warning("⚠️ Permission Required")
            if st.button("Connect to Shopify"):
                api_key = st.secrets["SHOPIFY_API_KEY"]
                # CRITICAL: This is the specific list of permissions
                scopes = "read_orders,read_products,read_customers"
                redirect_uri = "https://urbannue-data-pro-n9nzm7h4zeyxuvkqt5lmys.streamlit.app" 
                install_url = f"https://{shop_input}/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}"
                st.markdown(f"**[Click here to Authorize Urbannue]({install_url})**")

# 6. Analysis Engine
st.divider()

if "token" in st.session_state:
    st.subheader(f"Analyzing: {shop_input}")
    
    try:
        session = shopify.Session(shop_input, "2024-01", st.session_state["token"])
        shopify.ShopifyResource.activate_session(session)
        orders = shopify.Order.find(limit=50)
        shopify.ShopifyResource.clear_session()
        
        if orders:
            order_list = [{"ID": o.name, "Total": float(o.total_price), "Date": o.created_at} for o in orders]
            df = pd.DataFrame(order_list)

            k1, k2, k3 = st.columns(3)
            k1.metric("Orders Found", len(df))
            k2.metric("Total Revenue", f"₹{df['Total'].sum():,.2f}")
            k3.metric("Avg Value", f"₹{df['Total'].mean():,.2f}")

            st.write("### 📦 Live Order Data")
            st.dataframe(df, use_container_width=True)

            query = st.chat_input("Ask about your sales trends...")
            if query:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-3-flash-preview')
                with st.status("AI Analyzing Data...", expanded=True):
                    context = f"Store: {shop_input}. Data: {df.to_json(orient='records')}"
                    response = model.generate_content(f"{context}\n\nUser Question: {query}")
                    st.markdown(response.text)
        else:
            st.info("The store is connected, but I couldn't find any orders. Ensure your test orders are marked as 'Paid'.")
            
    except Exception as e:
        if "403" in str(e):
            st.error("🚨 **Access Denied.** Your current connection doesn't have 'Order' permissions. Please use the **Reset & Re-authorize** button in the sidebar.")
        else:
            st.error(f"Error: {e}")
else:
    st.info("Please link your store in the sidebar to begin.")
