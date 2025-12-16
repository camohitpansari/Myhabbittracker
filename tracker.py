uimport streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection # NEW IMPORT

# --- Configuration & Setup ---
# *** IMPORTANT: Replace the URL below with the SHAREABLE LINK of your Google Sheet ***
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZBukf2CZVvCKWhuDq6VHvZNKem-ZQ_caT8irYUiDHy0/edit?usp=drivesdk" 

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
# --- App Layout ---
st.set_page_config(page_title="Visual Habit Tracker", page_icon="📝", layout="wide")
st.title("📝 Gamified Habit Tracker & Reflection")

# Load data (Uses the new Google Sheets function)
df = load_data()

# --- Sidebar: Habit Management ---
st.sidebar.header("➕ Add New Habit")
new_habit = st.sidebar.text_input("Habit Name:", placeholder="e.g., Meditate for 10 min")

if st.sidebar.button("Add Habit"):
    if new_habit and new_habit not in get_all_habits(df):
        new_row = pd.DataFrame([{"Date": str(date.today()), "Habit": new_habit, "Status": False, "Is_Active": True, "Daily_Reflection": "", "Mood": UNSELECTED_MOOD_KEY}])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df)
        st.sidebar.success(f"Added: {new_habit}")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🗑️ Archive/Delete Habits")
all_habits = get_all_habits(df)

if all_habits:
    habit_to_manage = st.sidebar.selectbox(
        "Select Habit to manage:",
        options=all_habits
    )

    if st.sidebar.button("Archive Habit (Hide from Daily Log)", key="archive_btn"):
        df.loc[df["Habit"] == habit_to_manage, 'Is_Active'] = False
        save_data(df)
        st.sidebar.success(f"Habit '{habit_to_manage}' archived.")
        st.rerun()

    if st.sidebar.button("Activate Habit (Show in Daily Log)", key="activate_btn"):
        df.loc[df["Habit"] == habit_to_manage, 'Is_Active'] = True
        save_data(df)
        st.sidebar.success(f"Habit '{habit_to_manage}' activated.")
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.warning("🛑 **Permanent Deletion**")
    if st.sidebar.button("PERMANENTLY DELETE Habit & Data", type="primary", key="delete_btn"):
        df = df[df["Habit"] != habit_to_manage]
        save_data(df)
        st.sidebar.error(f"Habit '{habit_to_manage}' and ALL its data permanently deleted.")
        st.rerun()
else:
    st.sidebar.info("No habits to manage yet.")


# --- Main Section: Tracking ---
st.header("📅 Daily Log")

col1, col2 = st.columns([1, 3])
with col1:
    selected_date = st.date_input("Select Date", date.today())
    str_date = str(selected_date)

st.write(f"**Tracking for: {selected_date.strftime('%A, %d %B %Y')}**")

active_habits = get_active_habits(df)
if not active_habits:
    st.info("No active habits found. Add one or activate an archived habit in the sidebar!")
else:
    cols = st.columns(3)
    for i, habit in enumerate(active_habits):
        mask = (df["Date"] == str_date) & (df["Habit"] == habit)
        is_checked = False
        if not df[mask].empty:
            is_checked = bool(df.loc[mask, "Status"].values[0])
        
        current_streak = calculate_streak(df, habit)
        badge_label = get_badge(current_streak)

        with cols[i % 3]:
            st.markdown(f"### {habit}")
            st.caption(badge_label)
            
            clicked = st.checkbox("Done", value=is_checked, key=f"{habit}_{str_date}")
            
            if clicked != is_checked:
                if df[mask].empty:
                    new_entry = pd.DataFrame([{"Date": str_date, "Habit": habit, "Status": clicked, "Is_Active": True, "Daily_Reflection": "", "Mood": UNSELECTED_MOOD_KEY}])
                    df = pd.concat([df, new_entry], ignore_index=True)
                else:
                    df.loc[mask, 'Status'] = clicked
                    
                save_data(df)
                st.rerun()
            st.markdown("---")


# --- Mood Reflector Input ---
st.markdown("---")
st.header("✨ Mood Reflector")

current_mood_mask = (df["Date"] == str_date) & (df["Mood"] != UNSELECTED_MOOD_KEY)
current_mood_value = UNSELECTED_MOOD_KEY
if not df[current_mood_mask].empty:
    current_mood_value = df.loc[current_mood_mask, 'Mood'].iloc[0]

# --- SAFE MOOD SELECTBOX LOGIC ---
mood_keys = [UNSELECTED_MOOD_KEY] + sorted(MOOD_OPTIONS_MAP.keys())
mood_labels = [UNSELECTED_MOOD_LABEL] + [f"{k} {MOOD_OPTIONS_MAP[k].split(' ')[0]}" for k in sorted(MOOD_OPTIONS_MAP.keys())]
label_to_key_map = dict(zip(mood_labels, mood_keys))

if current_mood_value != UNSELECTED_MOOD_KEY:
    current_label = f"{current_mood_value} {MOOD_OPTIONS_MAP[current_mood_value].split(' ')[0]}"
    default_index = mood_labels.index(current_label)
else:
    default_index = 0

selected_mood_label = st.selectbox(
    "How was your general mood today?",
    options=mood_labels,
    index=default_index,
    format_func=lambda x: x.split(' ')[1] if x != UNSELECTED_MOOD_LABEL and len(x.split(' ')) > 1 else x, 
    key=f"mood_select_{str_date}"
)

selected_mood_value = label_to_key_map.get(selected_mood_label, UNSELECTED_MOOD_KEY)

# Update Data
if selected_mood_value != current_mood_value:
    df.loc[df["Date"] == str_date, 'Mood'] = selected_mood_value
    
    if not (df["Date"] == str_date).any():
        new_entry = pd.DataFrame([{"Date": str_date, "Habit": "Mood_Entry", "Status": False, "Is_Active": False, "Daily_Reflection": "", "Mood": selected_mood_value}])
        df = pd.concat([df, new_entry], ignore_index=True)
        
    save_data(df)
    
    if selected_mood_value != UNSELECTED_MOOD_KEY:
        st.success(f"Mood recorded as {MOOD_OPTIONS_MAP[selected_mood_value].split(' ')[0]}!")
    else:
        st.info("Mood entry cleared.")
        
    st.rerun()


# --- Daily Reflection Section ---
st.markdown("---")
st.header("💡 Daily Reflection")

reflection_mask = (df["Date"] == str_date)
current_reflection = ""

reflection_entries = df.loc[reflection_mask, 'Daily_Reflection'].dropna()
if not reflection_entries.empty:
    current_reflection = reflection_entries.iloc[0]


reflection_input = st.text_area(
    "What was your biggest win or challenge today? (Keep it brief)",
    value=current_reflection,
    height=100,
    key=f"reflection_{str_date}"
)

if reflection_input != current_reflection:
    if reflection_mask.any():
        df.loc[reflection_mask, 'Daily_Reflection'] = reflection_input
        save_data(df)
        st.success("Reflection saved!")
    elif reflection_input:
        st.warning("No habits tracked today. Reflection not fully saved yet.")
    

# --- Visual Graphics Section ---
st.header("📊 Progress Analytics")

if not df.empty and df["Status"].sum() > 0:
    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Leaderboard", "📈 Trends", "🔥 Heatmap", "📈 Mood Chart"])
    
    analysis_df = df[df['Status'].notna()].copy() 

    with tab1:
        # Leaderboard
        streak_data = []
        for h in get_all_habits(df):
            s = calculate_streak(df, h)
            total = len(df[(df["Habit"] == h) & (df["Status"] == True)])
            is_active = df.loc[df["Habit"] == h, 'Is_Active'].iloc[0]
            streak_data.append({"Habit": h, "Current Streak": s, "Badge": get_badge(s), "Total Completions": total, "Active": is_active})
        
        leaderboard_df = pd.DataFrame(streak_data).sort_values(by="Current Streak", ascending=False)
        st.dataframe(leaderboard_df, use_container_width=True, hide_index=True)

    with tab2:
        # Daily Trends (LINE CHART)
        st.subheader("Daily Productivity")
        daily_progress = analysis_df[analysis_df["Status"] == True].groupby("Date")["Status"].count()
        daily_progress.index = pd.to_datetime(daily_progress.index)
        daily_progress = daily_progress.sort_index()
        
        fig_line = px.line(
            daily_progress, 
            x=daily_progress.index, 
            y=daily_progress.values, 
            markers=True,
            labels={'y': 'Habits Completed', 'x': 'Date'},
            title='Daily Habits Completed Trend'
        )
        fig_line.update_layout(xaxis_title=None)
        st.plotly_chart(fig_line, use_container_width=True)
        
    with tab3:
        # Heatmap (Plotly)
        st.subheader("Visualizing Consistency")
        
        selected_heatmap_habit = st.selectbox(
            "Select Habit to view Heatmap (Includes archived habits):",
            options=get_all_habits(df)
        )
        if selected_heatmap_habit:
            create_heatmap_plotly(analysis_df, selected_heatmap_habit)
            
    with tab4:
        # Mood Chart
        st.subheader("Monthly Mood Tracking")
        create_mood_chart(df)
        
else:
    st.info("Start marking your habits to see the analytics!")

