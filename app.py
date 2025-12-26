import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
import time
from datetime import datetime, timedelta
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="V-Focus Audit", page_icon="☪️", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key = st.text_input("Enter Google Gemini API Key", type="password")
    user_niyyah = st.text_area("What is your Niyyah?", value="Learning AI, Islamic Finance, and Python.")
    
# --- MAIN APP ---
st.title("☪️ V-Focus: Digital Soul Audit")
st.write("Upload your `watch-history.json` to analyze your habits.")

uploaded_file = st.file_uploader("Upload JSON File", type="json")

# --- HELPER FUNCTIONS ---
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
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return ["Error"] * len(titles_list)

# --- LOGIC ---
if uploaded_file:
    # 1. LOAD DATA
    try:
        data = json.load(uploaded_file)
        
        # Clean Data Logic
        clean_data = []
        for entry in data:
            # Check different key formats (Google changes them sometimes)
            title = entry.get('title', '').replace("Watched ", "")
            time_str = entry.get('time', '')
            
            # Only keep valid video entries (ignore ads/empty)
            if title and time_str and "https://" not in title:
                clean_data.append({'Title': title, 'Time': time_str})
        
        if not clean_data:
            st.error("❌ No valid videos found in JSON. Is this the right file?")
            st.stop()

        df = pd.DataFrame(clean_data)
        df['Time'] = pd.to_datetime(df['Time'], format='ISO8601') # Standard Google format
        
        st.success(f"✅ Successfully loaded {len(df)} videos.")

        # 2. SHOW METRICS (Native Streamlit Components - No CSS Issues)
        now = df['Time'].max()
        df_1m = df[df['Time'] >= (now - timedelta(days=30))]
        df_12m = df[df['Time'] >= (now - timedelta(days=365))]

        # Creates clean, native metric cards
        col1, col2 = st.columns(2)
        col1.metric("Videos (Last 30 Days)", len(df_1m))
        col2.metric("Videos (Last 12 Months)", len(df_12m))

        # 3. DEBUG VIEW (Check if data looks right)
        with st.expander("👀 View Raw Data (Debug)"):
            st.dataframe(df.head(10))

    except Exception as e:
        st.error(f"Error processing file: {e}")
        st.stop()

    # 4. THE AI AUDIT
    st.divider()
    st.header("🤖 Run AI Analysis")
    
    if not api_key:
        st.warning("⚠️ Please enter your API Key in the sidebar to run the AI analysis.")
    else:
        if st.button("🚀 Audit My Last 50 Videos"):
            
            # Setup AI
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Prepare Batch
            df_audit = df.sort_values(by='Time', ascending=False).head(50)
            titles = df_audit['Title'].tolist()
            
            results = []
            progress_text = "Auditing your Niyyah..."
            my_bar = st.progress(0, text=progress_text)

            # Run Batch (Chunk size 10)
            batch_size = 10
            for i in range(0, len(titles), batch_size):
                batch = titles[i:i+batch_size]
                categories = classify_batch(batch, user_niyyah, model)
                
                for t, c in zip(batch, categories):
                    results.append({'Category': c, 'Title': t})
                
                my_bar.progress(min((i + batch_size) / len(titles), 1.0))
                time.sleep(1)

            my_bar.empty()
            
            # Visualization
            res_df = pd.DataFrame(results)
            
            # Filter errors
            res_df = res_df[res_df['Category'].isin(['Aligned', 'Neutral', 'Distraction'])]

            if not res_df.empty:
                st.subheader("Results")
                
                # Pie Chart
                fig = px.pie(res_df, names='Category', hole=0.4,
                             color='Category',
                             color_discrete_map={
                                 'Aligned': '#00CC96',
                                 'Neutral': '#AB63FA', 
                                 'Distraction': '#EF553B'
                             })
                st.plotly_chart(fig, use_container_width=True)
                
                # Table
                st.write("### Audit Log")
                st.dataframe(res_df)
            else:
                st.error("AI returned errors. Check your API Key or try again.")