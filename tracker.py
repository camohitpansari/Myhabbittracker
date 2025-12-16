import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
import matplotlib.pyplot as plt
import calmap # Library for creating the heatmap calendar

# --- Configuration & Setup ---
DATA_FILE = "habit_data.csv"

# Badge Definitions
BADGE_TIERS = {
    1: "🌟 New Start",
    7: "🏆 Bronze Star",
    30: "🥈 Silver Champion",
    90: "🥇 Gold Titan"
}

def load_data():
    """Loads the habit data from CSV."""
    if not os.path.exists(DATA_FILE):
        # Initial DataFrame structure
        return pd.DataFrame(columns=["Date", "Habit", "Status", "Is_Active", "Daily_Reflection"])
    
    df = pd.read_csv(DATA_FILE)
    df["Date"] = df["Date"].astype(str)
    
    # Ensure necessary columns exist for backward compatibility
    if 'Is_Active' not in df.columns:
        df['Is_Active'] = True
    if 'Daily_Reflection' not in df.columns:
        df['Daily_Reflection'] = ""
    
    return df

def save_data(df):
    """Saves the dataframe to CSV."""
    df.to_csv(DATA_FILE, index=False)

def get_active_habits(df):
    """Returns a list of unique habits that are currently active."""
    if df.empty:
        return []
    # Get unique habits that have at least one entry marked as Active=True
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

# --- Heatmap Generation Function ---
def create_heatmap(df, habit_name):
    """Generates the calendar heatmap for a specific habit."""
    
    heatmap_data = df[(df['Habit'] == habit_name) & (df['Status'] == True)].copy()
    
    if heatmap_data.empty:
        st.info(f"No successful logs yet for {habit_name} to generate a heatmap.")
        return

    heatmap_data['Date'] = pd.to_datetime(heatmap_data['Date'])
    heatmap_data = heatmap_data.set_index('Date')['Status'].resample('D').count().fillna(0)
    
    fig, ax = calmap.calendarplot(
        heatmap_data, 
        daylabels='MTWTFSS', 
        cmap='Greens',
        linewidth=1,
        linecolor='white',
        fig_kws=dict(figsize=(15, 6)),
        yearlabel_kws=dict(color='black', fontsize=14),
        fillcolor='lightgray',
        monthlabel='name',
        suptitle=f'Consistency Heatmap for: {habit_name}'
    )
    
    st.pyplot(fig)


# --- App Layout ---
st.set_page_config(page_title="Visual Habit Tracker", page_icon="📝", layout="wide")
st.title("📝 Gamified Habit Tracker & Reflection")

# Load data
df = load_data()

# --- Sidebar: Manage Habits (ADD) ---
st.sidebar.header("➕ Add New Habit")
new_habit = st.sidebar.text_input("Habit Name:", placeholder="e.g., Meditate for 10 min")

if st.sidebar.button("Add Habit"):
    if new_habit and new_habit not in get_all_habits(df):
        # Initialize the new habit with default values
        new_row = pd.DataFrame([{"Date": str(date.today()), "Habit": new_habit, "Status": False, "Is_Active": True, "Daily_Reflection": ""}])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df)
        st.sidebar.success(f"Added: {new_habit}")
        st.rerun()

# --- Sidebar: Manage Habits (ARCHIVE/DELETE) ---
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
    # Display Habits in a Grid
    cols = st.columns(3)
    for i, habit in enumerate(active_habits):
        # 1. Get Data for this date/habit
        mask = (df["Date"] == str_date) & (df["Habit"] == habit)
        is_checked = False
        if not df[mask].empty:
            is_checked = bool(df.loc[mask, "Status"].values[0])
        
        # 2. Calculate Streak and Badge
        current_streak = calculate_streak(df, habit)
        badge_label = get_badge(current_streak)

        # 3. Display UI
        with cols[i % 3]:
            st.markdown(f"### {habit}")
            st.caption(badge_label)
            
            # Checkbox interaction
            clicked = st.checkbox("Done", value=is_checked, key=f"{habit}_{str_date}")
            
            # Save logic (Only update Status)
            if clicked != is_checked:
                if df[mask].empty:
                    # Create a new row for this date
                    new_entry = pd.DataFrame([{"Date": str_date, "Habit": habit, "Status": clicked, "Is_Active": True, "Daily_Reflection": ""}])
                    df = pd.concat([df, new_entry], ignore_index=True)
                else:
                    df.loc[mask, 'Status'] = clicked
                    
                save_data(df)
                st.rerun()
            st.markdown("---")


# --- Daily Reflection Section ---
st.markdown("---")
st.header("💡 Daily Reflection")

# Get any existing reflection note for the selected date
reflection_mask = (df["Date"] == str_date)
current_reflection = ""

# Since reflections are per day, we can just grab the first non-empty reflection for the date
# (assuming the reflection will be the same across all habit rows for a given day)
reflection_entries = df.loc[reflection_mask, 'Daily_Reflection'].dropna()
if not reflection_entries.empty:
    current_reflection = reflection_entries.iloc[0]


reflection_input = st.text_area(
    "What was your biggest win or challenge today? (Keep it brief)",
    value=current_reflection,
    height=100,
    key=f"reflection_{str_date}"
)

# Save Reflection when input changes
if reflection_input != current_reflection:
    if reflection_mask.any():
        # Update the reflection column for ALL rows on the selected date
        df.loc[reflection_mask, 'Daily_Reflection'] = reflection_input
        save_data(df)
        st.success("Reflection saved!")
    elif reflection_input:
        # If no habits were tracked today, but the user writes a reflection, we need to create one dummy row to save it
        st.warning("No habits tracked today. Reflection not saved yet.")
    
# --- Visual Graphics Section ---
st.header("📊 Progress Analytics")

if not df.empty and df["Status"].sum() > 0:
    tab1, tab2, tab3 = st.tabs(["🏆 Leaderboard", "📈 Trends", "🔥 Heatmap Calendar"])
    
    analysis_df = df[df['Status'].notna()].copy() 

    with tab1:
        # Leaderboard
        streak_data = []
        for h in get_all_habits(df):
            s = calculate_streak(df, h)
            total = len(df[(df["Habit"] == h) & (df["Status"] == True)])
            # Get the current active status from the first entry of the habit
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
        # Heatmap
        st.subheader("Visualizing Consistency")
        
        selected_heatmap_habit = st.selectbox(
            "Select Habit to view Heatmap (Includes archived habits):",
            options=get_all_habits(df)
        )
        if selected_heatmap_habit:
            create_heatmap(analysis_df, selected_heatmap_habit)
        
else:
    st.info("Start marking your habits to see the analytics!")