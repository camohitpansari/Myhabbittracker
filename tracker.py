import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
import plotly.express as px
import plotly.graph_objects as go

# --- Configuration & Setup ---
DATA_FILE = "habit_data.csv"

# Badge Definitions
BADGE_TIERS = {
    1: "🌟 New Start",
    7: "🏆 Bronze Star",
    30: "🥈 Silver Champion",
    90: "🥇 Gold Titan"
}

# Mood Definitions and Value Mapping (for chart plotting)
MOOD_OPTIONS = {
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

# Map emoji index to a numerical value for charting (1=Lowest, 10=Highest)
# We will use the index number directly as the chart value.
MOOD_VALUE_MAP = {index: index for index in MOOD_OPTIONS.keys()}


def load_data():
    """Loads the habit data from CSV."""
    if not os.path.exists(DATA_FILE):
        # Add Mood column to initial DataFrame structure
        return pd.DataFrame(columns=["Date", "Habit", "Status", "Is_Active", "Daily_Reflection", "Mood"])
    
    df = pd.read_csv(DATA_FILE)
    df["Date"] = df["Date"].astype(str)
    
    # Ensure necessary columns exist for backward compatibility
    if 'Is_Active' not in df.columns:
        df['Is_Active'] = True
    if 'Daily_Reflection' not in df.columns:
        df['Daily_Reflection'] = ""
    if 'Mood' not in df.columns: # Add new column if missing
        df['Mood'] = 0 # Default to 0 (No Mood Set)
    
    return df

def save_data(df):
    """Saves the dataframe to CSV."""
    df.to_csv(DATA_FILE, index=False)

def get_active_habits(df):
    """Returns a list of unique habits that are currently active."""
    if df.empty:
        return []
    return list(df[df['Is_Active'] == True]["Habit"].unique())

def get_all_habits(df):
    """Returns a list of all unique habits, active or archived."""
    if df.empty:
        return []
    return list(df["Habit"].unique())


def calculate_streak(df, habit_name):
    """Calculates consecutive days (streak) for a specific habit."""
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
    """Returns the highest badge achieved for a given streak."""
    if streak == 0:
        return "❄️ No Streak"
    
    badge = ""
    for threshold in sorted(BADGE_TIERS.keys(), reverse=True):
        if streak >= threshold:
            badge = BADGE_TIERS[threshold]
            break
    
    return f"{badge} ({streak} Days)"

# --- Heatmap Generation Function using Plotly ---
def create_heatmap_plotly(df, habit_name):
    """Generates a calendar heatmap for a specific habit using Plotly."""
    
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
    df_plot['Year'] = df_plot['Date'].dt.year
    df_plot['Month'] = df_plot['Date'].dt.month_name().str[:3]
    df_plot['Week'] = df_plot['Date'].dt.isocalendar().week.astype(int)
    df_plot['DayOfWeek'] = df_plot['Date'].dt.day_name().str[:3]
    
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

# --- Mood Chart Function ---
def create_mood_chart(df):
    """Generates a monthly line chart of the user's mood."""
    
    # Filter for unique mood entries per day
    mood_data = df[df['Mood'] != 0].copy()
    mood_data['Date'] = pd.to_datetime(mood_data['Date'])
    
    # Select only the first mood recorded for each day
    mood_series = mood_data.drop_duplicates(subset='Date', keep='first').set_index('Date')['Mood']

    if mood_series.empty:
        st.info("No mood entries found yet.")
        return
    
    # Map the numerical mood back to the emoji label for better tooltip/display
    mood_df = pd.DataFrame({'Mood_Value': mood_series.values, 'Date': mood_series.index})
    mood_df['Mood_Label'] = mood_df['Mood_Value'].map({k: v.split(' ')[0] for k, v in MOOD_OPTIONS.items()})

    fig = px.line(
        mood_df,
        x="Date",
        y="Mood_Value",
        markers=True,
        title="Monthly Mood Trend",
        line_shape='spline' # Smoother line
    )

    # Customize the Y-axis to show the emoji labels instead of numbers
    fig.update_yaxes(
        tickvals=list(MOOD_OPTIONS.keys()),
        ticktext=[v.split(' ')[0] for v in MOOD_OPTIONS.values()], # Show only the emoji
        title='Mood',
        range=[min(MOOD_OPTIONS.keys()) - 0.5, max(MOOD_OPTIONS.keys()) + 0.5]
    )

    # Add tooltips to show the full description
    fig.update_traces(
        hovertemplate="Date: %{x}<br>Mood: %{customdata}<extra></extra>",
        customdata=mood_df['Mood_Label']
    )
    
    fig.update_layout(xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)


# --- App Layout ---
st.set_page_config(page_title="Visual Habit Tracker", page_icon="📝", layout="wide")
st.title("📝 Gamified Habit Tracker & Reflection")

# Load data
df = load_data()

# --- Sidebar: Habit Management ---
st.sidebar.header("➕ Add New Habit")
new_habit = st.sidebar.text_input("Habit Name:", placeholder="e.g., Meditate for 10 min")

if st.sidebar.button("Add Habit"):
    if new_habit and new_habit not in get_all_habits(df):
        new_row = pd.DataFrame([{"Date": str(date.today()), "Habit": new_habit, "Status": False, "Is_Active": True, "Daily_Reflection": "", "Mood": 0}])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df)
        st.sidebar.success(f"Added: {new_habit}")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🗑️ Archive/Delete Habits")
all_habits = get_all_habits(df)

# ... (Rest of sidebar logic for Archive/Delete remains the same) ...
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
                    new_entry = pd.DataFrame([{"Date": str_date, "Habit": habit, "Status": clicked, "Is_Active": True, "Daily_Reflection": "", "Mood": 0}])
                    df = pd.concat([df, new_entry], ignore_index=True)
                else:
                    df.loc[mask, 'Status'] = clicked
                    
                save_data(df)
                st.rerun()
            st.markdown("---")


# --- Mood Reflector Input ---
st.markdown("---")
st.header("✨ Mood Reflector")

# Extract the current mood value for the selected date
current_mood_mask = (df["Date"] == str_date) & (df["Mood"] != 0)
current_mood_value = 0
if not df[current_mood_mask].empty:
    current_mood_value = df.loc[current_mood_mask, 'Mood'].iloc[0]

# Prepare options for the selectbox
mood_list = [f"{index} {label.split(' ')[0]}" for index, label in MOOD_OPTIONS.items()]
mood_display_options = ["(Select Mood)"] + [MOOD_OPTIONS[i] for i in sorted(MOOD_OPTIONS.keys())]

# Determine the index of the current mood for the selectbox default value
if current_mood_value != 0:
    default_index = list(MOOD_OPTIONS.keys()).index(current_mood_value) + 1 # +1 for the "(Select Mood)" option
else:
    default_index = 0

selected_mood_label = st.selectbox(
    "How was your general mood today?",
    options=mood_display_options,
    index=default_index,
    format_func=lambda x: x.split(' ')[0], # Show only the emoji
    key=f"mood_select_{str_date}"
)

# Extract the selected mood index (1-10)
selected_mood_value = 0
if selected_mood_label != "(Select Mood)":
    # The format is "1 ☺️ Happy", so we extract the first part (the index)
    selected_mood_value = int(selected_mood_label.split(' ')[0])

# Update Data
if selected_mood_value != current_mood_value:
    # Set the mood column for ALL habit entries on the selected date
    df.loc[df["Date"] == str_date, 'Mood'] = selected_mood_value
    
    # If no habits were tracked, ensure at least one row exists to save the mood/reflection
    if not (df["Date"] == str_date).any():
        new_entry = pd.DataFrame([{"Date": str_date, "Habit": "Mood_Entry", "Status": False, "Is_Active": False, "Daily_Reflection": "", "Mood": selected_mood_value}])
        df = pd.concat([df, new_entry], ignore_index=True)
        
    save_data(df)
    st.success(f"Mood recorded as {selected_mood_label.split(' ')[0]}!")
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
        # Daily Trends
        st.subheader("Daily Productivity")
        daily_progress = analysis_df[analysis_df["Status"] == True].groupby("Date")["Status"].count()
        daily_progress.index = pd.to_datetime(daily_progress.index)
        daily_progress = daily_progress.sort_index()
        st.bar_chart(daily_progress, color="#ff4b4b")
        
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
        # NEW Mood Chart
        st.subheader("Monthly Mood Tracking")
        create_mood_chart(df)
        
else:
    st.info("Start marking your habits to see the analytics!")
