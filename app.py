import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
import time
from datetime import datetime, timedelta
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="V-Focus Audit", page_icon="☪️", layout="wide")

# --- CSS FOR MODERN LOOK ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .metric-card { background-color: #0E1117; padding: 20px; border-radius: 10px; border: 1px solid #30363D; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key = st.text_input("Enter Google Gemini API Key", type="password", help="Get one for free at aistudio.google.com")
    st.info("We do not store your key. It is used only for this session.")
    
    user_niyyah = st.text_area("What is your Niyyah (Intention)?", value="Learning AI, Islamic Finance, and Python.")
    
    st.divider()
    st.write("Built with ❤️ by a V-Focus Researcher")

# --- MAIN APP ---
st.title("☪️ V-Focus: Digital Soul Audit")
st.markdown("### Are your algorithms serving your Niyyah or your Nafs?")
st.write("Upload your YouTube Watch History (`watch-history.json`) to analyze your digital diet.")

uploaded_file = st.file_uploader("Upload JSON File", type="json")

# --- HELPER FUNCTIONS ---

def classify_batch(titles_list, niyyah_text, model):
    """Sends a batch of titles to Gemini for classification."""
    prompt = f"""
    My Intention (Niyyah) is: {niyyah_text}.
    
    Classify EACH of these YouTube video titles into exactly one of these 3 categories:
    - 'Aligned' (Beneficial, Education, Faith, Skills)
    - 'Neutral' (News, Hobbies, Sleep, innocent relaxation, DIY videos, aesthetics, Did you know)
    - 'Distraction' (Pranks, Drama, Dance, Funny, Tricks, Clickbait, Mindless Entertainment, Shorts)
    
    TITLES:
    {json.dumps(titles_list)}
    
    RETURN ONLY a JSON list of strings. Example: ["Aligned", "Distraction"]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return ["Error"] * len(titles_list)

# --- LOGIC ---

if uploaded_file and api_key:
    # 1. SETUP AI
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
    except:
        st.error("Invalid API Key or Model Error.")
        st.stop()

    # 2. LOAD DATA
    try:
        data = json.load(uploaded_file)
        # Normalize: Google Takeout format varies. We look for 'title' and 'time'.
        # We flatten the list to get a clean DataFrame
        clean_data = []
        for entry in data:
            if 'title' in entry and 'titleUrl' in entry: # Filter ads roughly
                clean_data.append({
                    'Title': entry['title'].replace("Watched ", ""),
                    'Time': entry['time']
                })
        
        df = pd.DataFrame(clean_data)
        df['Time'] = pd.to_datetime(df['Time'], format='ISO8601')
        
        st.success(f"✅ Loaded {len(df)} videos successfully.")

    except Exception as e:
        st.error(f"Error parsing JSON: {e}")
        st.stop()

    # 3. DATE FILTERING (1 Month & 12 Months)
    now = df['Time'].max() # Use the latest date in the file as "Now"
    one_month_ago = now - timedelta(days=30)
    one_year_ago = now - timedelta(days=365)
    
    df_1m = df[df['Time'] >= one_month_ago]
    df_12m = df[df['Time'] >= one_year_ago]

    # --- DISPLAY STATS ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<div class='metric-card'><h2>{len(df_1m)}</h2><p>Videos Watched (Last 30 Days)</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><h2>{len(df_12m)}</h2><p>Videos Watched (Last 12 Months)</p></div>", unsafe_allow_html=True)

    # 4. AI ANALYSIS (The "Audit")
    st.divider()
    st.header("🤖 The AI Audit")
    
    if st.button("Run Audit (Analyze Last 50 Videos)"):
        with st.spinner("Consulting the AI..."):
            # We take the most recent 50 videos (Batching to save time/quota)
            # Sorting just in case
            df_sorted = df.sort_values(by='Time', ascending=False).head(50)
            titles = df_sorted['Title'].tolist()
            
            # Run Batch Classification (Splitting into chunks of 10)
            results = []
            batch_size = 10
            progress_bar = st.progress(0)
            
            for i in range(0, len(titles), batch_size):
                batch = titles[i:i+batch_size]
                categories = classify_batch(batch, user_niyyah, model)
                
                # Match results
                for t, c in zip(batch, categories):
                    results.append({'Title': t, 'Category': c})
                
                progress_bar.progress((i + batch_size) / len(titles))
                time.sleep(1) # Rate limit safety
            
            audit_df = pd.DataFrame(results)
            
            # --- RESULTS VISUALIZATION ---
            st.subheader("Your Distraction Score")
            
            # Filter out Errors
            audit_df = audit_df[audit_df['Category'] != "Error"]
            
            counts = audit_df['Category'].value_counts().reset_index()
            counts.columns = ['Category', 'Count']
            
            # Donut Chart
            fig = px.pie(counts, values='Count', names='Category', hole=0.5, 
                         color='Category',
                         color_discrete_map={
                             'Aligned': '#10B981', 
                             'Neutral': '#94A3B8', 
                             'Distraction': '#F43F5E'
                         })
            fig.update_layout(title_text="Analysis of Recent Habits", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            st.write("### Detailed Log")
            st.dataframe(audit_df)
            
elif uploaded_file and not api_key:
    st.warning("Please enter an API Key in the sidebar to start the analysis.")