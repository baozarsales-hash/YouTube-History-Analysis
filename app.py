import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
import time
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(page_title="V-Focus Audit", page_icon="☪️", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key = st.text_input("Enter Google Gemini API Key", type="password")
    user_niyyah = st.text_area("What is your Niyyah?", value="Learning AI, Islamic Finance, and Python.")

st.title("☪️ V-Focus: Debug Mode")

uploaded_file = st.file_uploader("Upload JSON File", type="json")

# --- ROBUST CLASSIFIER ---
def classify_batch(titles_list, niyyah_text, model):
    prompt = f"""
    My Intention (Niyyah) is: {niyyah_text}.
    Classify these video titles into exactly one of these 3 categories:
    - 'Aligned'
    - 'Neutral'
    - 'Distraction'
    
    TITLES: {json.dumps(titles_list)}
    
    RETURN ONLY a JSON list of strings. Example: ["Aligned", "Distraction"]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        # Find the JSON list inside the text (sometimes AI adds extra words)
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != -1:
            clean_json = text[start:end]
            return json.loads(clean_json)
        else:
            return [f"Error: Invalid JSON format. Raw: {text[:50]}..."] * len(titles_list)
    except Exception as e:
        return [f"API Error: {str(e)}"] * len(titles_list)

# --- MAIN LOGIC ---
if uploaded_file:
    # Load Data
    data = json.load(uploaded_file)
    clean_data = []
    for entry in data:
        title = entry.get('title', '').replace("Watched ", "")
        time_str = entry.get('time', '')
        if title and time_str and "https://" not in title:
            clean_data.append({'Title': title, 'Time': time_str})
    
    df = pd.DataFrame(clean_data)
    df['Time'] = pd.to_datetime(df['Time'], format='ISO8601')
    
    # Show Metrics
    col1, col2 = st.columns(2)
    col1.metric("Videos (Last 30 Days)", len(df[df['Time'] >= (df['Time'].max() - timedelta(days=30))]))
    col2.metric("Videos (Last 12 Months)", len(df[df['Time'] >= (df['Time'].max() - timedelta(days=365))]))

    st.divider()
    
    if not api_key:
        st.warning("Please enter API Key to run audit.")
    else:
        if st.button("🚀 Audit My Last 20 Videos"): # Reduced to 20 for safer testing
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Prepare Batch
            df_audit = df.sort_values(by='Time', ascending=False).head(20)
            titles = df_audit['Title'].tolist()
            
            results = []
            progress_bar = st.progress(0, text="Auditing...")
            
            # Create a placeholder to print logs
            log_area = st.empty()

            # Batch Size 5 (Smaller batch = less likely to fail)
            batch_size = 5
            for i in range(0, len(titles), batch_size):
                batch = titles[i:i+batch_size]
                
                # Run AI
                categories = classify_batch(batch, user_niyyah, model)
                
                # PRINT THE RAW OUTPUT SO WE CAN SEE THE ERROR
                log_area.text(f"Batch {i//batch_size + 1}: {categories}")
                
                for t, c in zip(batch, categories):
                    results.append({'Category': c, 'Title': t})
                
                progress_bar.progress(min((i + batch_size) / len(titles), 1.0))
                time.sleep(2) # Slower to avoid rate limits

            # Show Results
            res_df = pd.DataFrame(results)
            st.write("### Raw Results Table")
            st.dataframe(res_df) # Show everything, even errors

            # Only show chart if we have valid data
            valid_df = res_df[res_df['Category'].isin(['Aligned', 'Neutral', 'Distraction'])]
            if not valid_df.empty:
                fig = px.pie(valid_df, names='Category', color='Category', 
                             color_discrete_map={'Aligned':'#00CC96', 'Neutral':'#AB63FA', 'Distraction':'#EF553B'})
                st.plotly_chart(fig)