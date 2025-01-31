import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import random

# ========== KONFIGURATION ==========
THEME_COLORS = {
    "light": {
        "primary": "#1E88E5",
        "secondary": "#FF6D00",
        "background": "#FFFFFF",
        "text": "#000000"
    },
    "dark": {
        "primary": "#90CAF9",
        "secondary": "#FFAB40",
        "background": "#121212",
        "text": "#FFFFFF"
    }
}

LANGUAGES = {
    "sv": {
        "title": "AI-drivet Schemaläggningssystem",
        "subtitle": "Optimerad personalplanering för vården",
        "add_staff": "Lägg till personal",
        "experience_labels": {
            1: "1 - Nyexaminerad/Erfarenhetssökande",
            2: "2 - Grundläggande erfarenhet",
            3: "3 - Erfaren",
            4: "4 - Mycket erfaren",
            5: "5 - Expert",
            6: "6 - Avdelningsansvarig"
        },
    },
    "en": {
        "title": "AI-Powered Staff Scheduling",
        "subtitle": "Optimized Workforce Management for Healthcare",
        "add_staff": "Add Staff",
        "experience_labels": {
            1: "1 - New graduate/Entry-level",
            2: "2 - Basic experience",
            3: "3 - Experienced",
            4: "4 - Highly experienced",
            5: "5 - Expert",
            6: "6 - Department lead"
        },
    }
}

def initialize_session():
    if "staff" not in st.session_state:
        st.session_state.staff = []
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    if "language" not in st.session_state:
        st.session_state.language = "sv"

initialize_session()

def get_css(theme):
    colors = THEME_COLORS["dark" if st.session_state.dark_mode else "light"]
    return f"""
    <style>
        .main {{
            background-color: {colors['background']};
            color: {colors['text']};
        }}
        .stDataFrame {{
            border: 2px solid {colors['primary']};
            border-radius: 10px;
        }}
        .stButton>button {{
            background: {colors['primary']} !important;
            color: white !important;
        }}
    </style>
    """

def generate_fair_schedule(staff, min_daily_score=20, days_in_week=7):
    shifts = defaultdict(int)
    schedule = {day: {"staff": [], "score": 0} for day in range(days_in_week)}
    
    for day in schedule:
        daily_team = []
        daily_score = 0
        available_workers = sorted(staff, key=lambda x: (shifts[x["name"]], -x["experience"]))
        
        for worker in available_workers:
            if daily_score >= min_daily_score:
                break
            if (shifts[worker["name"]] <= min(shifts.values())) or (random.random() < 0.3):
                daily_team.append(worker["name"])
                daily_score += worker["experience"]
                shifts[worker["name"]] += 1
        
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

def staff_input_section(lang):
    st.subheader(lang["add_staff"])
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        name = st.text_input("Namn", key="new_name")
    with col2:
        exp = st.selectbox(
            "Erfarenhetsnivå",
            options=list(lang["experience_labels"].keys()),
            format_func=lambda x: lang["experience_labels"][x],
            key="new_exp"
        )
    with col3:
        if st.button("➕ Lägg till", use_container_width=True):
            if name.strip():
                st.session_state.staff.append({"name": name.strip(), "experience": exp})
            else:
                st.error("Ange ett namn")

def staff_list_editor(lang):
    if st.session_state.staff:
        df = pd.DataFrame(st.session_state.staff)
        edited_df = st.data_editor(
            df,
            column_config={
                "experience": {
                    "label": "Erfarenhetsnivå",
                    "type": "number",
                    "help": "Välj från 1 (nybörjare) till 6 (expert)"
                }
            },
            use_container_width=True,
            num_rows="dynamic"
        )
        st.session_state.staff = edited_df.to_dict("records")

def main():
    lang = LANGUAGES[st.session_state.language]
    
    header_col1, header_col2, header_col3 = st.columns([2, 1, 1])
    with header_col1:
        st.image("vardschema.png", width=200)
    with header_col2:
        st.session_state.language = st.selectbox("🌐 Språk", ["sv", "en"])
    with header_col3:
        st.session_state.dark_mode = st.toggle("🌙 Mörkt läge")
    
    st.title(lang["title"])
    st.caption(lang["subtitle"])
    st.markdown(get_css(st.session_state.dark_mode), unsafe_allow_html=True)
    
    with st.expander("❓ Hur använder jag detta verktyg?", expanded=True):
        st.markdown("""
        1. **Lägg till personal** med formuläret nedan
        2. Justera inställningar i sidofältet
        3. Generera och granska schema
        4. Exportera eller spara resultatet
        """)
    
    staff_input_section(lang)
    staff_list_editor(lang)
    
    with st.sidebar:
        st.header("⚙️ Inställningar")
        min_score = st.slider(
            "Minsta erfarenhetspoäng per dag",
            10, 50, 20,
            help="Totalt erfarenhetspoäng som krävs per skift"
        )
        
        st.divider()
        st.subheader("Schemainställningar")
        week_start = st.date_input("Veckostart")
        max_shifts = st.number_input("Max antal skift per person", 3, 7, 5)
        
        st.divider()
        if st.button("🗑️ Rensa all personaldata"):
            st.session_state.staff = []
            st.rerun()
    
    if st.button("🚀 Generera schema", use_container_width=True):
        if not st.session_state.staff:
            st.error("Lägg till personal först")
        else:
            with st.spinner("🤖 AI optimerar ditt schema..."):
                schedule, shifts = generate_fair_schedule(st.session_state.staff, min_score)
                
                st.success("✅ Schema genererat!")
                days = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
                schedule_df = pd.DataFrame([
                    {"Dag": days[i], "Personal": ", ".join(schedule[i]["staff"]), "Poäng": schedule[i]["score"]}
                    for i in range(7)
                ])
                
                st.dataframe(
                    schedule_df.style.background_gradient(subset=["Poäng"], cmap="Blues"),
                    use_container_width=True,
                    hide_index=True
                )
                
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.bar(shifts.keys(), shifts.values(), color=THEME_COLORS["dark" if st.session_state.dark_mode else "light"]["primary"])
                plt.xticks(rotation=45)
                plt.ylabel("Antal skift")
                st.pyplot(fig)
                
                st.download_button(
                    "📥 Ladda ner schema som Excel",
                    data=schedule_df.to_csv(index=False).encode("utf-8"),
                    file_name="schema.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()
