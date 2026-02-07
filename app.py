import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. Page Config & Theme
st.set_page_config(page_title="Urbannue Pro | Intelligence", layout="wide")

# 2. Access Security
if "authenticated" not in st.session_state:
    st.title("🔒 Urbannue Pro Access")
    pwd = st.text_input("Enter Access Code", type="password")
    if pwd == st.secrets["ACCESS_PASSWORD"]:
        st.session_state["authenticated"] = True
        st.rerun()
    else:
        st.stop()

# 3. Main Product Interface
st.title("🏆 Urbannue Pro | Business Intelligence")

with st.sidebar:
    st.image("https://via.placeholder.com/150?text=Urbannue") # Replace with your logo later
    st.header("Store Connection")
    shop_url = st.text_input("Shopify Store URL", placeholder="brand-name.myshopify.com")
    
    if st.button("Connect Store"):
        # This is the "Premium" install link
        api_key = st.secrets["SHOPIFY_API_KEY"]
        install_url = f"https://{shop_url}/admin/oauth/authorize?client_id={api_key}&scope=read_orders,read_products&redirect_uri={st.secrets.get('REDIRECT_URL', 'https://your-app-name.streamlit.app')}"
        st.markdown(f"**[Click here to authorize Urbannue]({install_url})**")

# 4. AI Consultant Logic
st.info("👋 Welcome to Urbannue. Upload your latest sales data or connect via API above.")
query = st.chat_input("Ask your business consultant a question...")

if query:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-3-flash-preview')
    st.write(f"Analyzing data for: *{query}*...")
    # Your existing AI logic follows here...
