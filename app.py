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

st.title("☪️ V-Focus: Digital Soul Audit")

# --- SMART MODEL SELECTOR ---
def get_best_model():
    """Asks Google which models are available and picks the best one."""
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Prefer Flash (Fast/Cheap)
                if 'flash' in m.name:
                    return m.name
        # Fallback to Pro if Flash not found
        return "models/gemini-pro"
    except:
        return "models/gemini-pro"

# --- CLASSIFIER ---
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
        # Extract JSON list from text
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != -1:
            clean_json = text[start:end]
            return json.loads(clean_json)
        else:
            return ["Error"] * len(titles_list)
    except Exception as e:
        return [f"Error"] * len(titles_list)

# --- MAIN APP ---
uploaded_file = st.file_uploader("Upload JSON File", type="json")

if uploaded_file:
    # 1. LOAD DATA
    try:
        data = json.load(uploaded_file)
        clean_data = []
        for entry in data:
            title = entry.get('title', '').replace("Watched ", "")
            time_str = entry.get('time', '')
            if title and time_str and "https://" not in title:
                clean_data.append({'Title': title, 'Time': time_str})
        
        df = pd.DataFrame(clean_data)
        df['Time'] = pd.to_datetime(df['Time'], format='ISO8601')
        
        # Metrics
        now = df['Time'].max()
        col1, col2 = st.columns(2)
        col1.metric("Videos (Last 30 Days)", len(df[df['Time'] >= (now - timedelta(days=30))]))
        col2.metric("Videos (Last 12 Months)", len(df[df['Time'] >= (now - timedelta(days=365))]))

    except Exception as e:
        st.error(f"Error parsing file: {e}")
        st.stop()

    st.divider()

    # 2. RUN AUDIT
    if not api_key:
        st.warning("Please enter API Key to run audit.")
    else:
        if st.button("🚀 Audit My Last 20 Videos"):
            
            # Setup AI
            genai.configure(api_key=api_key)
            
            # AUTO-DETECT MODEL NAME
            model_name = get_best_model()
            st.info(f"Using AI Model: `{model_name}`") # User can see which model is used
            model = genai.GenerativeModel(model_name)
            
            # Prepare Data
            df_audit = df.sort_values(by='Time', ascending=False).head(20)
            titles = df_audit['Title'].tolist()
            
            results = []
            progress_bar = st.progress(0, text="Auditing...")
            
            # Run Batch
            batch_size = 5
            for i in range(0, len(titles), batch_size):
                batch = titles[i:i+batch_size]
                categories = classify_batch(batch, user_niyyah, model)
                
                for t, c in zip(batch, categories):
                    results.append({'Category': c, 'Title': t})
                
                progress_bar.progress(min((i + batch_size) / len(titles), 1.0))
                time.sleep(1) # Safety delay

            # Visualization
            res_df = pd.DataFrame(results)
            
            # Filter for valid categories
            valid_df = res_df[res_df['Category'].isin(['Aligned', 'Neutral', 'Distraction'])]
            
            if not valid_df.empty:
                st.subheader("Results")
                fig = px.pie(valid_df, names='Category', hole=0.4, 
                             color='Category',
                             color_discrete_map={'Aligned':'#00CC96', 'Neutral':'#AB63FA', 'Distraction':'#EF553B'})
                st.plotly_chart(fig)
                
                st.write("### Audit Log")
                st.dataframe(res_df)
            else:
                st.error("The AI returned errors. It might be overloaded. Try again in 1 minute.")
                st.write("Debug info:", res_df)