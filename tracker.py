import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection # NEW IMPORT

# --- Configuration & Setup ---
# *** IMPORTANT: Replace the URL below with the SHAREABLE LINK of your Google Sheet ***
GOOGLE_SHEET_URL = "YOUR_GOOGLE_SHEET_URL_HERE" 

# Badge Definitions (No Change)
BADGE_TIERS = {
    1: "🌟 New Start",
    7: "🏆 Bronze Star",
    30: "🥈 Silver Champion",
    90: "🥇 Gold Titan"
}

# Mood Definitions and Value Mapping (No Change)
MOOD_OPTIONS_MAP = {
    1: "☺️ Happy",
    2: "😑 Meh",
    3: "😞 Disappointed",
    4: "😭 Crying",
    5: "🥰 Loved",
    6: "👼 Peaceful",
    7: "🥳 Excited",
    8: "🤩 Amazed",
    9: "🥱 Tired",
    10: "🤧 Sick"
}

UNSELECTED_MOOD_KEY = 0
UNSELECTED_MOOD_LABEL = "--- Select Your Mood ---"

# --- NEW Data Loading and Saving Functions using Google Sheets ---
# Initialize connection and cache data to prevent excessive reloads
conn = st.connection("gsheets", type=GSheetsConnection)
REQUIRED_COLUMNS = ["Date", "Habit", "Status", "Is_Active", "Daily_Reflection", "Mood"]

@st.cache_data(ttl=5) # Cache data for 5 seconds
def load_data():
    """Loads the habit data from Google Sheets."""
    try:
        df = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="TrackingLog", usecols=REQUIRED_COLUMNS, ttl=5)
        df["Date"] = df["Date"].astype(str)
        # Ensure 'Mood' column is numeric/integer
        df['Mood'] = pd.to_numeric(df['Mood'], errors='coerce').fillna(UNSELECTED_MOOD_KEY).astype(int)
        
        # Ensure all required columns exist
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = ''
        
        return df
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        st.info("Please ensure your Google Sheet URL is correct and the Sheet is shared as 'Editor'.")
        # Return an empty dataframe to allow the app to run
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

def save_data(df):
    """Saves the dataframe back to Google Sheets."""
    try:
        conn.write(df=df, spreadsheet=GOOGLE_SHEET_URL, worksheet="TrackingLog")
        # Clear cache to force reload on the next run
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error saving data to Google Sheets: {e}")

# --- Helper Functions (No Major Change) ---
def get_active_habits(df):
    if df.empty:
        return []
    return list(df[df['Is_Active'] == True]["Habit"].unique())

def get_all_habits(df):
    if df.empty:
        return []
    return list(df["Habit"].unique())

def calculate_streak(df, habit_name):
    completed_dates = df[(df["Habit"] == habit_name) & (df["Status"] == True)]["Date"].unique()
    if len(completed_dates) == 0:
        return 0
    streak = 0
    check_date = date.today()
    if str(check_date) not in completed_dates:
        check_date = check_date - timedelta(days=1)
    while str(check_date) in completed_dates:
        streak += 1
        check_date = check_date - timedelta(days=1)
    return streak

def get_badge(streak):
    if streak == 0:
        return "❄️ No Streak"
    badge = ""
    for threshold in sorted(BADGE_TIERS.keys(), reverse=True):
        if streak >= threshold:
            badge = BADGE_TIERS[threshold]
            break
    return f"{badge} ({streak} Days)"

# --- Visualization Functions (No Major Change) ---
def create_heatmap_plotly(df, habit_name):
    # ... (Code for Heatmap remains the same) ...
    heatmap_data = df[(df['Habit'] == habit_name) & (df['Status'] == True)].copy()
    if heatmap_data.empty:
        st.info(f"No successful logs yet for {habit_name} to generate a heatmap.")
        return
    heatmap_data['Date'] = pd.to_datetime(heatmap_data['Date'])
    start_date = date.today() - timedelta(days=365)
    full_range = pd.date_range(start=start_date, end=date.today(), freq='D')
    successes = heatmap_data.set_index('Date')['Status'].resample('D').count().reindex(full_range, fill_value=0)
    dates = successes.index
    levels = successes.values
    df_plot = pd.DataFrame({'Date': dates, 'Count': levels})
    df_plot['DayOfWeek'] = df_plot['Date'].dt.day_name().str[:3]
    df_plot['Week'] = df_plot['Date'].dt.isocalendar().week.astype(int)
    day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    fig = go.Figure(data=go.Heatmap(
        x=df_plot['DayOfWeek'],
        y=df_plot['Week'], 
        z=df_plot['Count'],
        colorscale='Greens',
        hoverinfo='text',
        text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Completed: {c} Times" for d, c in zip(df_plot['Date'], df_plot['Count'])],
        ygap=3,
        xgap=3,
    ))
    fig.update_layout(
        title=f'Consistency Heatmap for: {habit_name} (Last Year)',
        xaxis=dict(title='Day of Week', categoryorder='array', categoryarray=day_order),
        yaxis=dict(title='Week of Year', autorange='reversed'),
        height=600,
        margin=dict(t=50, b=0, l=0, r=0)
    )
    st.plotly_chart(fig, use_container_width=True)

def create_mood_chart(df):
    # ... (Code for Mood Chart remains the same) ...
    mood_data = df[df['Mood'] != UNSELECTED_MOOD_KEY].copy()
    mood_data['Date'] = pd.to_datetime(mood_data['Date'])
    mood_series = mood_data.drop_duplicates(subset='Date', keep='first').set_index('Date')['Mood']
    if mood_series.empty:
        st.info("No mood entries found yet.")
        return
    mood_df = pd.DataFrame({'Mood_Value': mood_series.values, 'Date': mood_series.index})
    mood_df['Mood_Label'] = mood_df['Mood_Value'].map({k: v.split(' ')[0] for k, v in MOOD_OPTIONS_MAP.items()})

    fig = px.line(
        mood_df, x="Date", y="Mood_Value", markers=True, title="Monthly Mood Trend", line_shape='spline'
    )
    fig.update_yaxes(
        tickvals=list(MOOD_OPTIONS_MAP.keys()),
        ticktext=[v.split(' ')[0] for v in MOOD_OPTIONS_MAP.values()],
        title='Mood',
        range=[min(MOOD_OPTIONS_MAP.keys()) - 0.5, max(MOOD_OPTIONS_MAP.keys()) + 0.5]
    )
    fig.update_traces(
        hovertemplate="Date: %{x}<br>Mood: %{customdata}<extra></extra>",
        customdata=mood_df['Mood_Label']
    )
    fig.update_layout(xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)


# --- App Layout (Daily Log and Sidebar logic need minor adjustments to use new Mood keys) ---

# ... (The rest of the app logic remains largely the same, but uses the new data functions) ...
