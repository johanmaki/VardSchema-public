# pages/1_Chefsida.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import random

# ========== KONFIGURATION ==========
THEME_COLORS = {
    "light": {"primary": "#1E88E5", "secondary": "#FF6D00"},
    "dark": {"primary": "#90CAF9", "secondary": "#FFAB40"}
}

LANGUAGES = {
    "sv": {
        "title": "AI-drivet Schemaläggningssystem",
        "days": ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"],
        "add_staff": "Lägg till personal",
        "experience_labels": {
            1: "1 - Nyexaminerad", 
            2: "2 - Grundläggande",
            3: "3 - Erfaren",
            4: "4 - Mycket erfaren",
            5: "5 - Expert",
            6: "6 - Avdelningsansvarig"
        }
    }
}

# ========== INITIERING ==========
def init_session():
    if "staff" not in st.session_state:
        st.session_state.staff = []
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

# ========== HUVUDFUNKTIONER ==========
def generate_schedule(staff, min_daily_score=20):
    shifts = defaultdict(int)
    schedule = {day: {"staff": [], "score": 0} for day in range(7)}
    
    total_exp = sum(m["experience"] for m in staff)
    if total_exp < min_daily_score * 7:
        raise ValueError(f"Otillräcklig erfarenhet ({total_exp} vs {min_daily_score*7})")

    for day in schedule:
        daily_team = []
        daily_score = 0
        available = sorted(staff, key=lambda x: (shifts[x["name"]], -x["experience"]))
        
        for worker in available:
            if daily_score >= min_daily_score:
                break
            if shifts[worker["name"]] <= min(shifts.values(), default=0) or random.random() < 0.3:
                daily_team.append(worker["name"])
                daily_score += worker["experience"]
                shifts[worker["name"]] += 1
        
        schedule[day]["staff"] = daily_team
        schedule[day]["score"] = daily_score
    
    return schedule, shifts

# ========== GRÄNSSNITTET ==========
def show_interface():
    init_session()
    lang = LANGUAGES["sv"]
    
    # Header
    st.title(f"👨💼 Chefssida - {st.session_state.hospital}")
    st.caption("Schemaläggningsverktyg för chefer")
    
    # Temainställningar
    st.session_state.dark_mode = st.sidebar.toggle("Mörkt läge", value=False)
    
    # Personalhantering
    with st.expander("➕ Lägg till personal", expanded=True):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            name = st.text_input("Namn")
        with col2:
            exp = st.selectbox("Erfarenhet", options=lang["experience_labels"].keys(), 
                             format_func=lambda x: lang["experience_labels"][x])
        with col3:
            if st.button("Lägg till", disabled=not name.strip()):
                st.session_state.staff.append({"name": name.strip(), "experience": exp})
                st.rerun()

    # Personalredigerare
    if st.session_state.staff:
        df = pd.DataFrame(st.session_state.staff)
        edited_df = st.data_editor(
            df,
            column_config={"experience": {"help": "Erfarenhetsnivå 1-6"}},
            use_container_width=True,
            num_rows="dynamic"
        )
        st.session_state.staff = edited_df.to_dict("records")

    # Schemagenerering
    st.sidebar.divider()
    min_score = st.sidebar.slider("Minsta poäng/dag", 10, 50, 20)
    
    if st.button("🚀 Generera schema"):
        if not st.session_state.staff:
            st.error("Lägg till personal först")
        else:
            with st.spinner("Optimerar schema..."):
                try:
                    schedule, shifts = generate_schedule(st.session_state.staff, min_score)
                    
                    # Visa schema
                    schedule_df = pd.DataFrame([
                        {"Dag": lang["days"][i], 
                         "Personal": ", ".join(schedule[i]["staff"]), 
                         "Poäng": schedule[i]["score"]}
                        for i in range(7)
                    ])
                    
                    st.dataframe(
                        schedule_df.style.background_gradient(subset=["Poäng"], cmap="Blues"),
                        hide_index=True
                    )
                    
                    # Visualisering
                    fig, ax = plt.subplots()
                    ax.bar(shifts.keys(), shifts.values(), color=THEME_COLORS["dark" if st.session_state.dark_mode else "light"]["primary"])
                    plt.xticks(rotation=45)
                    st.pyplot(fig)
                    
                except Exception as e:
                    st.error(f"Fel: {str(e)}")

    # Logga ut
    st.sidebar.divider()
    if st.sidebar.button("🔒 Logga ut"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ========== SIDHANTERING ==========
def main():
    if "user_type" not in st.session_state or st.session_state.user_type != "chef":
        st.error("Åtkomst nekad")
        st.stop()
    
    st.set_page_config(page_title="Chefsida", layout="wide")
    show_interface()

if __name__ == "__main__":
    main()