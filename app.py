import streamlit as st
import pandas as pd
import openai

st.set_page_config(page_title="Urbannue Data Insights", layout="wide")
st.title("📊 Urbannue: Shopify Data Pro")

# Professional Sidebar for Credentials
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API Key", type="password")
    uploaded_file = st.file_uploader("Upload Shopify Orders CSV", type="csv")

if not api_key:
    st.warning("Please enter your OpenAI API Key to start.")

if uploaded_file and api_key:
    df = pd.read_csv(uploaded_file)
    st.success("Data Loaded Successfully!")
    
    # Show a preview for the user
    with st.expander("View Raw Data"):
        st.dataframe(df.head(10))

    query = st.text_input("Ask a question about your sales (e.g. 'Show top 5 customers by spend')")

    if query:
        client = openai.OpenAI(api_key=api_key)
        
        # This prompt forces the AI to be a Business Analyst
        system_prompt = f"""
        You are a Shopify Data Expert. Dataset columns: {list(df.columns)}
        Task: Write Python code using pandas to answer the question: {query}
        Rules: 
        1. Use variable name 'df' for the dataframe.
        2. Output ONLY the code block, no text.
        3. Use plotly for charts if requested.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": system_prompt}]
        )
        
        code = response.choices[0].message.content.replace("```python", "").replace("```", "")
        
        st.write("### Result:")
        try:
            exec(code)
        except Exception as e:
            st.error(f"Error in analysis: {e}")
