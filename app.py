import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import random

# ========== CONFIGURATION ==========
THEME_COLOR = "#1E88E5"
SECONDARY_COLOR = "#FF6D00"
BG_COLOR = "#F5F5F5"

# ========== CUSTOM CSS ==========
st.markdown(f"""
    <style>
        .reportview-container {{
            background: {BG_COLOR};
        }}
        .main .block-container {{
            padding-top: 2rem;
        }}
        h1 {{
            color: {THEME_COLOR};
        }}
        .stDataFrame {{
            border: 2px solid {THEME_COLOR};
            border-radius: 10px;
        }}
        .stButton>button {{
            background: {THEME_COLOR};
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }}
        .stDownloadButton>button {{
            background: {SECONDARY_COLOR} !important;
        }}
        footer {{visibility: hidden;}}
        #MainMenu {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# ========== FUNCTIONS ==========
def generate_fair_schedule(staff, min_daily_score=20, days_in_week=7):
    shifts = defaultdict(int)
    schedule = {day: {"staff": [], "score": 0} for day in range(days_in_week)}
    
    for day in schedule:
        daily_team = []
        daily_score = 0
        available_workers = sorted(staff, key=lambda x: (shifts[x["name"]], -x["experience"]))
        
        # AI-powered scheduling
        for worker in available_workers:
            if daily_score >= min_daily_score:
                break
            if (shifts[worker["name"]] <= min(shifts.values())) or (random.random() < 0.3):
                daily_team.append(worker["name"])
                daily_score += worker["experience"]
                shifts[worker["name"]] += 1
        
        # Fallback mechanism
        while daily_score < min_daily_score:
            for worker in available_workers:
                if worker["name"] not in daily_team:
                    daily_team.append(worker["name"])
                    daily_score += worker["experience"]
                    shifts[worker["name"]] += 1
                    break
        
        schedule[day]["staff"] = daily_team
        schedule[day]["score"] = daily_score
    
    return schedule, shifts

# ========== HEADER SECTION ==========
col1, col2 = st.columns([1, 4])
with col1:
    st.image("vardschema.png", width=150)  # Your custom logo
with col2:
    st.title("AI-Powered Staff Scheduling")
    st.caption("Optimized Workforce Management for Healthcare Institutions")

# ========== INPUT SECTION ==========
with st.expander("📋 How to Use This Tool", expanded=True):
    st.markdown("""
        1. **Add Staff** below using format: `Name, Experience (1-6)`
        2. Set **Minimum Daily Experience** in sidebar
        3. Click **Generate Schedule**
        4. **Download** or **Share** your schedule
    """)

input_col, preview_col = st.columns(2)
with input_col:
    st.subheader("➕ Add Staff Members")
    input_text = st.text_area(
        "Enter staff (one per line):",
        height=200,
        placeholder="Example:\nDr. Andersson,6\nNurse Berg,4\n...",
        label_visibility="collapsed"
    )

# ========== DATA PROCESSING ==========
staff = []
if input_text:
    try:
        for line in input_text.split('\n'):
            line = line.strip()
            if line:
                name, exp = line.rsplit(',', 1)
                staff.append({
                    "name": name.strip(),
                    "experience": int(exp.strip())
                })
        
        # Validation
        if len(staff) == 0:
            st.error("⚠️ Please add at least one staff member")
            st.stop()
            
        invalid_exp = [m for m in staff if not 1 <= m["experience"] <= 6]
        if invalid_exp:
            st.error(f"❌ Invalid experience levels: {[m['name'] for m in invalid_exp]}")
            st.stop()
            
        with preview_col:
            st.subheader("👥 Team Preview")
            preview_df = pd.DataFrame(staff)
            st.dataframe(
                preview_df.style.format({"experience": "⭐ {}"}),
                use_container_width=True,
                hide_index=True
            )
            
    except Exception as e:
        st.error(f"❌ Format error: {str(e)}\nPlease use format: Name, Experience")
        st.stop()

# ========== CONTROLS ==========
with st.sidebar:
    st.header("⚙️ Settings")
    min_score = st.slider("Minimum Daily Experience", 10, 30, 20, 
                         help="Combined experience required per shift")
    
    st.divider()
    st.markdown("**Schedule Options**")
    week_start = st.date_input("Week Starting", value="today")
    enable_night_shift = st.checkbox("Include Night Shifts", True)

# ========== SCHEDULE GENERATION ==========
if st.button("🚀 Generate Schedule", use_container_width=True):
    if not staff:
        st.error("Please add staff members first")
    else:
        with st.spinner("🧠 Optimizing schedule using AI..."):
            schedule, shifts = generate_fair_schedule(staff, min_daily_score=min_score)
            
            # Schedule Display
            st.success("✅ Schedule Generated Successfully!")
            
            # Convert to DataFrame
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            schedule_data = []
            for day in schedule:
                schedule_data.append({
                    "Day": days[day],
                    "Staff": ", ".join(schedule[day]["staff"]),
                    "Total Experience": schedule[day]["score"]
                })
            
            # Enhanced DataFrame display
            schedule_df = pd.DataFrame(schedule_data)
            st.dataframe(
                schedule_df.style.applymap(lambda x: f"color: {THEME_COLOR}", subset=["Day"])
                               .bar(subset=["Total Experience"], color=f"{THEME_COLOR}55"),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Staff": st.column_config.ListColumn(
                        "Team Members",
                        help="Optimized team composition for each shift"
                    )
                }
            )
            
            # Visualization
            st.subheader("📊 Shift Distribution Analysis")
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.bar(shifts.keys(), shifts.values(), color=THEME_COLOR)
            plt.title("Fairness Distribution Across Team Members", pad=20)
            plt.xticks(rotation=45, ha='right')
            plt.ylabel("Number of Shifts")
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            st.pyplot(fig)
            
            # Statistics Cards
            total_shifts = sum(shifts.values())
            avg_shifts = total_shifts / len(shifts)
            fairness_score = 1 - (max(shifts.values()) - min(shifts.values())) / avg_shifts
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Shifts", total_shifts)
            col2.metric("Average Shifts/Person", f"{avg_shifts:.1f}")
            col3.metric("Fairness Score", f"{fairness_score:.0%}")
            
            # Export System
            st.divider()
            st.subheader("📤 Export Options")
            
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                # CSV Download
                csv = schedule_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name='hospital_schedule.csv',
                    mime='text/csv',
                    use_container_width=True
                )
            
            with export_col2:
                # Calendar Integration
                if st.button("Add to Google Calendar", use_container_width=True):
                    st.info("Calendar integration coming soon!")
