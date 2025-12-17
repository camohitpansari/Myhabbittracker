import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# --- 1. Configuration & Connection Setup ---
# Replace 'your-project-id' with your actual Google Cloud Project ID
PROJECT_ID = "habittracker-streamlit-project" 
DATASET_NAME = "habit_tracker_db"
TABLE_NAME = "TrackingLog"

# Define the full table reference for SQL queries
FULL_TABLE_REF = f"`{PROJECT_ID}.{DATASET_NAME}.{TABLE_NAME}`"

# We use the 'sql' connection type which is widely supported
conn = st.connection("sql")

# Column names must match your BigQuery/Google Sheet exactly
REQUIRED_COLUMNS = ["Date", "Habit", "Status", "Is_Active", "Daily_Reflection", "Mood"]

# Badge & Mood Definitions
BADGE_TIERS = {1: "🌟 New Start", 7: "🏆 Bronze Star", 30: "🥈 Silver Champion", 90: "🥇 Gold Titan"}
MOOD_OPTIONS_MAP = {1: "☺️ Happy", 2: "😑 Meh", 3: "😞 Disappointed", 4: "😭 Crying", 5: "🥰 Loved", 
                    6: "👼 Peaceful", 7: "🥳 Excited", 8: "🤩 Amazed", 9: "🥱 Tired", 10: "🤧 Sick"}
UNSELECTED_MOOD_KEY = 0
UNSELECTED_MOOD_LABEL = "--- Select Your Mood ---"

# --- 2. Data Loading ---
@st.cache_data(ttl=60) # Refreshes every minute
def load_data():
    try:
        # SQL Query to pull data from the BigQuery linked table
        query = f"SELECT * FROM {FULL_TABLE_REF}"
        df = conn.query(query)
        
        # Data Cleaning: Convert BigQuery types to Python-friendly types
        df["Date"] = df["Date"].astype(str)
        df['Mood'] = pd.to_numeric(df['Mood'], errors='coerce').fillna(UNSELECTED_MOOD_KEY).astype(int)
        
        # Convert Status and Is_Active to true booleans
        df['Status'] = df['Status'].apply(lambda x: str(x).lower() in ('true', '1', 'yes'))
        df['Is_Active'] = df['Is_Active'].apply(lambda x: str(x).lower() in ('true', '1', 'yes'))
        
        return df
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

# --- 3. Helper Functions ---
def calculate_streak(df, habit_name):
    completed_dates = df[(df["Habit"] == habit_name) & (df["Status"] == True)]["Date"].unique()
    if len(completed_dates) == 0: return 0
    streak, check_date = 0, date.today()
    if str(check_date) not in completed_dates:
        check_date -= timedelta(days=1)
    while str(check_date) in completed_dates:
        streak += 1
        check_date -= timedelta(days=1)
    return streak

def get_badge(streak):
    if streak == 0: return "❄️ No Streak"
    badge = ""
    for threshold in sorted(BADGE_TIERS.keys(), reverse=True):
        if streak >= threshold:
            badge = BADGE_TIERS[threshold]
            break
    return f"{badge} ({streak} Days)"

# --- 4. Visualizations (Plotly) ---
def create_heatmap_plotly(df, habit_name):
    heatmap_data = df[(df['Habit'] == habit_name) & (df['Status'] == True)].copy()
    if heatmap_data.empty:
        st.info("No data for heatmap yet.")
        return
    heatmap_data['Date'] = pd.to_datetime(heatmap_data['Date'])
    fig = go.Figure(data=go.Heatmap(
        x=heatmap_data['Date'].dt.day_name().str[:3],
        y=heatmap_data['Date'].dt.isocalendar().week,
        z=[1]*len(heatmap_data),
        colorscale='Greens', showscale=False
    ))
    fig.update_layout(title=f"Consistency: {habit_name}", height=300)
    st.plotly_chart(fig, use_container_width=True)

# --- 5. App Layout ---
st.set_page_config(page_title="Habit Tracker (BigQuery)", layout="wide")
st.title("📈 Habit Tracker Dashboard")

df = load_data()

if df.empty:
    st.warning("No data found. Please add entries to your Google Sheet.")
else:
    # Sidebar Info
    st.sidebar.success("✅ Connected to Google Sheet via BigQuery")
    st.sidebar.info("💡 Note: To log habits, update your Google Sheet directly. This dashboard will refresh automatically.")

    # Daily Status View
    st.header("📅 Current Streaks")
    active_habits = df[df['Is_Active'] == True]['Habit'].unique()
    
    cols = st.columns(len(active_habits) if len(active_habits) > 0 else 1)
    for i, habit in enumerate(active_habits):
        streak = calculate_streak(df, habit)
        with cols[i % len(cols)]:
            st.metric(label=habit, value=f"{streak} Days", delta=get_badge(streak))

    # Analytics Tabs
    tab1, tab2 = st.tabs(["🔥 Consistency Heatmap", "🎭 Mood Trends"])
    
    with tab1:
        sel_habit = st.selectbox("Select Habit", active_habits)
        if sel_habit:
            create_heatmap_plotly(df, sel_habit)
            
    with tab2:
        mood_df = df[df['Mood'] != UNSELECTED_MOOD_KEY].copy()
        if not mood_df.empty:
            mood_df['Date'] = pd.to_datetime(mood_df['Date'])
            fig_mood = px.line(mood_df, x='Date', y='Mood', title="Mood over Time", markers=True)
            st.plotly_chart(fig_mood, use_container_width=True)
