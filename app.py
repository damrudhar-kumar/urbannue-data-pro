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

# 3. Handle Shopify Callback
query_params = st.query_params
if "code" in query_params and "shop" in query_params:
    shop = query_params["shop"]
    code = query_params["code"]
    try:
        api_key = st.secrets["SHOPIFY_API_KEY"]
        api_secret = st.secrets["SHOPIFY_API_SECRET"]
        conn = requests.post(
            f"https://{shop}/admin/oauth/access_token",
            json={"client_id": api_key, "client_secret": api_secret, "code": code}
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
            if st.button("Re-connect / Update Permissions"):
                st.session_state.pop("token")
                st.rerun()
        else:
            st.warning("⚠️ Permission Needed.")
            if st.button("Connect to Shopify"):
                api_key = st.secrets["SHOPIFY_API_KEY"]
                # CRITICAL: Added 'read_orders' to the scope here
                scopes = "read_orders,read_products"
                redirect_uri = "https://urbannue-data-pro-n9nzm7h4zeyxuvkqt5lmys.streamlit.app" 
                install_url = f"https://{shop_input}/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}"
                st.markdown(f"**[Authorize Urbannue Now]({install_url})**")

# 6. Real-Time Data Analysis Logic
st.divider()

if "token" in st.session_state:
    st.subheader(f"Analyzing Live Data: {shop_input}")
    
    try:
        session = shopify.Session(shop_input, "2024-01", st.session_state["token"])
        shopify.ShopifyResource.activate_session(session)
        orders = shopify.Order.find(limit=50)
        shopify.ShopifyResource.clear_session()
        
        if orders:
            order_data = []
            for o in orders:
                order_data.append({
                    "Order ID": o.name,
                    "Total Price": float(o.total_price),
                    "Date": o.created_at,
                    "Items": len(o.line_items)
                })
            df = pd.DataFrame(order_data)

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Orders", len(df))
            k2.metric("Total Revenue", f"₹{df['Total Price'].sum():,.2f}")
            k3.metric("Avg. Order Value", f"₹{df['Total Price'].mean():,.2f}")

            st.write("### 📦 Recent Order Records")
            st.dataframe(df, use_container_width=True)

            query = st.chat_input("Ask about your sales trends...")
            if query:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-3-flash-preview')
                
                with st.status("Consulting Engine...", expanded=True):
                    data_json = df.to_json(orient='records')
                    full_prompt = f"Store: {shop_input}. Data: {data_json}. Request: {query}. Act as a Senior Business Analyst."
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
        else:
            st.info("No orders found. Ensure your test orders are 'Paid' and not 'Drafts'.")
    except Exception as e:
        if "403" in str(e):
            st.error("🚨 Permission Denied: You need to click 'Connect to Shopify' again to approve Order access.")
        else:
            st.error(f"Data Fetch Error: {e}")
else:
    st.info("Enter your store URL in the sidebar to begin.")
