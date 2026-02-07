import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Urbannue Data Insights", layout="wide")
st.title("📊 Urbannue: Shopify Data (Gemini Edition)")

with st.sidebar:
    st.header("Settings")
    gemini_key = st.text_input("Enter Gemini API Key", type="password")
    uploaded_file = st.file_uploader("Upload Shopify Orders CSV", type="csv")

if not gemini_key:
    st.info("Please enter your Gemini API Key from Google AI Studio to begin.")

if uploaded_file and gemini_key:
    # Configure Gemini
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    df = pd.read_csv(uploaded_file)
    st.success("Data Loaded!")
    
    with st.expander("View Data Preview"):
        st.dataframe(df.head(5))

    query = st.text_input("Ask a business question about your orders:")

    if query:
        # System Prompt for the BA logic
        prompt = f"""
        You are a Shopify Data Analyst. 
        Dataset Columns: {list(df.columns)}
        
        Question: {query}
        
        Task: Write ONLY the Python code using pandas to answer this. 
        - Use the variable 'df'.
        - Do not explain the code.
        - If the user asks for a chart, use streamlit's 'st.bar_chart' or 'st.line_chart'.
        - For text answers, use 'st.write()'.
        """
        
        try:
            response = model.generate_content(prompt)
            # Clean the code (remove markdown backticks)
            code = response.text.replace("```python", "").replace("```", "").strip()
            
            st.write("### Analysis:")
            exec(code)
        except Exception as e:
            st.error(f"Analysis failed. Error: {e}")
