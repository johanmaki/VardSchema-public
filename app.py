import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import random

# ======== AI Scheduling Logic ========
def generate_fair_schedule(staff, min_daily_score=20, days_in_week=7):
    shifts = defaultdict(int)
    schedule = {day: {"staff": [], "score": 0} for day in range(days_in_week)}
    
    for day in schedule:
        daily_team = []
        daily_score = 0
        available_workers = sorted(staff, key=lambda x: (shifts[x["name"]], -x["experience"]))
        
        # Build team to meet minimum score
        for worker in available_workers:
            if daily_score >= min_daily_score:
                break
            if (shifts[worker["name"]] <= min(shifts.values())) or (random.random() < 0.3):
                daily_team.append(worker["name"])
                daily_score += worker["experience"]
                shifts[worker["name"]] += 1
        
        # Force-add workers if score not met
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

# ======== Streamlit UI ========
st.set_page_config(page_title="AI Sjukhus Schemaläggare", layout="wide")

# Title and description
st.title("⚕️ AI-drivet Schemaläggningssystem för Sjukhus")
st.markdown("*Skapat för att automatisera personalplanering med rättvis fördelning och erfarenhetsbalans.*")

# Sidebar for inputs
with st.sidebar:
    st.header("Inställningar")
    min_score = st.slider("Minsta erfarenhetspoäng per dag", 10, 30, 20)
    uploaded_file = st.file_uploader("Ladda upp personaldata (Excel/CSV)", type=["csv", "xlsx"])

# Load staff data
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            staff_df = pd.read_csv(uploaded_file)
        else:
            staff_df = pd.read_excel(uploaded_file)
        
        # Validate required columns
        if "name" not in staff_df.columns or "experience" not in staff_df.columns:
            st.error("❌ Felaktig fil: CSV måste ha kolumnerna 'name' och 'experience'.")
            st.stop()  # Halt execution
        
        staff = staff_df.to_dict('records')
        
    except Exception as e:
        st.error(f"❌ Kunde inte läsa fil: {str(e)}")
        st.stop()
    
    if st.button("Generera Schema med AI"):
        with st.spinner("AI planerar ditt schema..."):
            schedule, shifts = generate_fair_schedule(staff, min_daily_score=min_score)
            
            # Display schedule
            days_se = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
            schedule_data = []
            for day in schedule:
                schedule_data.append({
                    "Dag": days_se[day],
                    "Personal": ", ".join(schedule[day]["staff"]),
                    "Erfarenhetspoäng": schedule[day]["score"]
                })
            
            st.success("✅ Schema genererat!")
            st.dataframe(pd.DataFrame(schedule_data), use_container_width=True)
            
            # Show shift distribution
            st.subheader("Skiftfördelning")
            fig, ax = plt.subplots()
            ax.bar(shifts.keys(), shifts.values(), color='#1e88e5')
            plt.xticks(rotation=45)
            plt.ylabel("Antal Skift")
            st.pyplot(fig)
            
            # Download button
            csv = pd.DataFrame(schedule_data).to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Ladda ner schema som CSV",
                data=csv,
                file_name='ai_genererat_schema.csv',
                mime='text/csv'
            )
else:
    st.info("ℹ️ Ladda upp en Excel/CSV-fil med personaldata för att börja.")
