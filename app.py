import streamlit as st
import pandas as pd
import google.generativeai as genai
from supabase import create_client, Client
import shopify
import requests
import time

# 1. Page Configuration
st.set_page_config(page_title="Urbannue Pro | Intelligence", layout="wide")

# 2. Supabase Connection
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

def clean_url(url):
    return url.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0].strip()

def save_token(shop, token):
    data = {"shop_url": clean_url(shop), "access_token": token}
    supabase.table("shopify_sessions").upsert(data).execute()

def get_stored_token(shop_url):
    shop = clean_url(shop_url)
    try:
        response = supabase.table("shopify_sessions").select("access_token").eq("shop_url", shop).execute()
        return response.data[0]['access_token'] if response.data else None
    except:
        return None

# 3. Handle Shopify OAuth Callback
query_params = st.query_params
if "code" in query_params and "shop" in query_params:
    shop = clean_url(query_params["shop"])
    code = query_params["code"]
    try:
        token_url = f"https://{shop}/admin/oauth/access_token"
        res = requests.post(token_url, json={
            "client_id": st.secrets["SHOPIFY_API_KEY"],
            "client_secret": st.secrets["SHOPIFY_API_SECRET"],
            "code": code
        }, timeout=15)
        access_token = res.json().get("access_token")
        if access_token:
            save_token(shop, access_token)
            st.session_state["token"] = access_token
            st.query_params.clear()
            st.success("Permissions Approved! Loading Dashboard...")
            time.sleep(1)
            st.rerun()
    except Exception as e:
        st.error(f"Handshake Error: {e}")

# 4. Access Security
if "authenticated" not in st.session_state:
    st.title("🔒 Urbannue Pro Login")
    pwd = st.text_input("Enter Access Code", type="password")
    if st.button("Unlock"):
        if pwd == st.secrets["ACCESS_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# 5. Dashboard Sidebar
st.title("🏆 Urbannue Pro | Business Intelligence")
with st.sidebar:
    st.header("Store Status")
    raw_url = st.text_input("Enter Store URL", placeholder="brand.myshopify.com")
    shop_input = clean_url(raw_url)
    
    if shop_input:
        token = get_stored_token(shop_input)
        if token and "token" not in st.session_state:
            st.session_state["token"] = token

        if "token" in st.session_state:
            st.success(f"✅ {shop_input} Linked")
            if st.button("Force Disconnect (Clear DB)"):
                supabase.table("shopify_sessions").delete().eq("shop_url", shop_input).execute()
                if "token" in st.session_state: del st.session_state["token"]
                st.rerun()
        else:
            st.warning("⚠️ Permission Needed")
            if st.button("Connect & Approve Orders"):
                api_key = st.secrets["SHOPIFY_API_KEY"]
                scopes = "read_orders,read_products"
                redirect_uri = "https://urbannue-data-pro-n9nzm7h4zeyxuvkqt5lmys.streamlit.app"
                # Added timestamp to force a fresh login screen
                auth_url = f"https://{shop_input}/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}&state={int(time.time())}"
                st.markdown(f"**[Step 2: Click to Authorize Orders]({auth_url})**")

# 6. Analysis Engine
st.divider()
if "token" in st.session_state and shop_input:
    try:
        session = shopify.Session(shop_input, "2024-04", st.session_state["token"])
        shopify.ShopifyResource.activate_session(session)
        orders = shopify.Order.find(limit=50, status="any")
        shopify.ShopifyResource.clear_session()
        
        if orders:
            df = pd.DataFrame([{"ID": o.name, "Total": float(o.total_price), "Date": o.created_at} for o in orders])
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Orders", len(df))
            c2.metric("Revenue", f"₹{df['Total'].sum():,.2f}")
            c3.metric("AOV", f"₹{df['Total'].mean():,.2f}")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No orders found. Please create a 'Paid' order in Shopify.")
    except Exception as e:
        st.error(f"System Error: {e}")
        if "403" in str(e):
            st.warning("This key does not have Order access. Please use the 'Force Disconnect' button above and re-authorize.")
