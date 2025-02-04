import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from collections import defaultdict
import random
import time

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
        "days": ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
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
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    }
}

# ========== INITIERING ==========
def initialize_session():
    if "staff" not in st.session_state:
        st.session_state.staff = []
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    if "language" not in st.session_state:
        st.session_state.language = "sv"

initialize_session()

# ========== ANPASSAD CSS ==========
def get_css():
    colors = THEME_COLORS["dark" if st.session_state.dark_mode else "light"]
    return f"""
    <style>
        .main {{
            background-color: {colors['background']};
            color: {colors['text']};
        }}
        .stTextInput>div>div>input, .stSelectbox>div>div>select {{
            color: {colors['text']} !important;
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

# ========== FUNKTIONER ==========
def generate_fair_schedule(staff, min_daily_score=20, days_in_week=7):
    shifts = defaultdict(int)
    schedule = {day: {"staff": [], "score": 0} for day in range(days_in_week)}
    
    total_experience = sum(m["experience"] for m in staff)
    if total_experience < min_daily_score:
        raise ValueError(f"Otillräcklig total erfarenhet ({total_experience}). Krävs minst " +min_daily_score+".")

    for day in schedule:
        daily_team = []
        daily_score = 0
        available_workers = sorted(staff, key=lambda x: (shifts[x["name"]], -x["experience"]))
        
        for worker in available_workers:
            if daily_score >= min_daily_score:
                break
            if (shifts[worker["name"]] <= min(shifts.values(), default=0)) or (random.random() < 0.3):
                daily_team.append(worker["name"])
                daily_score += worker["experience"]
                shifts[worker["name"]] += 1
        
        backup_attempts = 0
        while daily_score < min_daily_score and backup_attempts < 3:
            for worker in available_workers:
                if worker["name"] not in daily_team:
                    daily_team.append(worker["name"])
                    daily_score += worker["experience"]
                    shifts[worker["name"]] += 1
                    if daily_score >= min_daily_score:
                        break
            backup_attempts += 1

        if daily_score < min_daily_score:
            required = min_daily_score - daily_score
            raise ValueError(f"Kunde inte nå minimipoäng {min_daily_score}. Saknar {required} poäng")

        schedule[day]["staff"] = daily_team
        schedule[day]["score"] = daily_score
    
    return schedule, shifts

# ========== GRÄNSSNITTSKOMPONENTER ==========
def staff_input_section(lang):
    st.subheader(lang["add_staff"])
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        name = st.text_input("Namn", key="new_staff_name")
    with col2:
        exp = st.selectbox(
            "Erfarenhetsnivå",
            options=list(lang["experience_labels"].keys()),
            format_func=lambda x: lang["experience_labels"][x],
            key="new_staff_exp"
        )
    with col3:
        if st.button("➕ Lägg till", 
                    use_container_width=True,
                    key="add_staff_button"):
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
            num_rows="dynamic",
            key="staff_editor"
        )
        st.session_state.staff = edited_df.to_dict("records")

# ========== HUVUDLAYOUT ==========
def main():
    lang = LANGUAGES[st.session_state.language]
    
    # Header
    header_col1, header_col2, header_col3 = st.columns([2, 1, 1])
    with header_col1:
        st.image("vardschema.png", width=200)
    with header_col2:
        st.session_state.language = st.selectbox(
            "🌐 Språk",
            ["sv", "en"],
            key="language_selector"
        )
    with header_col3:
        st.session_state.dark_mode = st.toggle(
            "🌙 Mörkt läge",
            key="dark_mode_toggle"
        )
    
    st.title(lang["title"])
    st.caption(lang["subtitle"])
    st.markdown(get_css(), unsafe_allow_html=True)
    
    # Instruktioner
    with st.expander("❓ Hur använder jag detta verktyg? :)", expanded=True):
        st.markdown("""
        1. **Lägg till personal** med formuläret nedan
        2. Justera inställningar i sidofältet
        3. Generera och granska schema
        4. Exportera eller spara resultatet
        """)
    
    # Personalhantering
    staff_input_section(lang)
    staff_list_editor(lang)
    
    # Sidofältsinställningar
    with st.sidebar:
        st.header("⚙️ Inställningar", help="Globala inställningar för schemaläggning")
        min_score = st.slider(
            "Minsta erfarenhetspoäng per dag",
            10, 50, 20,
            key="min_score_slider",
            help="Totalt erfarenhetspoäng som krävs per skift"
        )
        
        st.divider()
        st.subheader("Schemainställningar")
        week_start = st.date_input(
            "Veckostart",
            key="week_start_date"
        )
        
        st.divider()
        if st.button("🗑️ Rensa all personaldata",
                    key="clear_data_button"):
            st.session_state.staff = []
            st.rerun()
    
    # Schemagenerering
    if st.button("🚀 Generera schema", 
                use_container_width=True,
                key="main_generate_button"):
        if not st.session_state.staff:
            st.error("Lägg till personal först")
        else:
            with st.spinner("🤖 AI optimerar ditt schema..."):
                try:
                    schedule, shifts = generate_fair_schedule(st.session_state.staff, min_score)
                    st.success("✅ Schema genererat!")
                    
                    # Visa schema
                    schedule_df = pd.DataFrame([
                        {
                            "Dag": lang["days"][i],
                            "Personal": ", ".join(schedule[i]["staff"]),
                            "Poäng": schedule[i]["score"]
                        }
                        for i in range(7)
                    ])
                    
                    st.dataframe(
                        schedule_df.style.background_gradient(subset=["Poäng"], cmap="Blues"),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Visualiseringar
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.bar(shifts.keys(), shifts.values(), 
                          color=THEME_COLORS["dark" if st.session_state.dark_mode else "light"]["primary"])
                    plt.xticks(rotation=45)
                    plt.ylabel("Antal skift")
                    st.pyplot(fig)
                    
                except ValueError as e:
                    st.error(f"Schemaläggningsfel: {str(e)}")
                except Exception as e:
                    st.error(f"Oväntat fel: {str(e)}")

if __name__ == "__main__":
    main()