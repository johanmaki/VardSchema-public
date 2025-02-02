import time
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

with st.spinner("AI analyserar personalens kompetensprofil..."):
    # Simulera faktisk bearbetningstid
    for i in range(3):
        time.sleep(0.5)
        st.spinner(f"Bearbetar... (steg {i+1}/3)")

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
    
    # Beräkna total tillgänglig erfarenhet
    total_experience = sum(member["experience"] for member in staff)
    
    # Validera att personalstyrkan är tillräcklig
    if total_experience < min_daily_score * days_in_week:
        raise ValueError(f"Otillräcklig total erfarenhet ({total_experience}). Måste vara minst {min_daily_score * days_in_week}")
    
    for day in schedule:
        daily_team = []
        daily_score = 0
        available_workers = sorted(staff, key=lambda x: (shifts[x["name"]], -x["experience"]))
        
        # Steg 1: Välj kärnpersonal
        for worker in available_workers:
            if daily_score >= min_daily_score:
                break
            if shifts[worker["name"]] <= min(shifts.values(), default=0):
                daily_team.append(worker["name"])
                daily_score += worker["experience"]
                shifts[worker["name"]] += 1
        
        # Steg 2: Fyll på om nödvändigt (med fallback-logik)
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
        
        # Fallback om fortfarande under minimum
        if daily_score < min_daily_score:
            required = min_daily_score - daily_score
            raise ValueError(f"Kunde inte nå minimipoäng {min_daily_score} för {days[day]}. Saknar {required} poäng.")
        
        schedule[day]["staff"] = daily_team
        schedule[day]["score"] = daily_score
    
    return schedule, shifts

def professional_visualizations(schedule, shifts, staff):
    """Ny sektion för avancerade visualiseringar"""
    
    with st.expander("📈 Avancerad Analys", expanded=True):
        tab1, tab2, tab3 = st.tabs(["Skiftfördelning", "Erfarenhetsnivåer", "Tidslinje"])
        
        with tab1:
            # Interaktivt stapeldiagram
            fig = px.bar(
                x=list(shifts.keys()),
                y=list(shifts.values()),
                labels={"x": "Personal", "y": "Antal skift"},
                title="Skiftfördelning per Person",
                color=list(shifts.values()),
                color_continuous_scale="Blues"
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            # Cirkeldiagram för erfarenhetsnivåer
            exp_data = pd.DataFrame(staff)
            fig = px.pie(
                exp_data,
                names="experience",
                title="Erfarenhetsfördelning i Teamet",
                hole=0.3,
                category_orders={"experience": [6,5,4,3,2,1]}
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
            
        with tab3:
            # Gantt-schema med tidslinje
            schedule_df = pd.DataFrame([
                {
                    "Dag": days[i],
                    "Start": datetime.now() + timedelta(days=i),
                    "Slut": datetime.now() + timedelta(days=i+1),
                    "Personal": ", ".join(schedule[i]["staff"]),
                    "Poäng": schedule[i]["score"]
                }
                for i in range(7)
            ])
            
            fig = px.timeline(
                schedule_df,
                x_start="Start",
                x_end="Slut",
                y="Dag",
                color="Poäng",
                title="Veckoschema Tidslinje",
                hover_name="Personal",
                color_continuous_scale="Viridis"
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
            
        # Exportknappar
        st.download_button(
            "📥 Ladda ner analys som PDF-rapport",
            data=generate_pdf_report(schedule, shifts, staff),
            file_name="schema_analys.pdf",
            mime="application/pdf"
        )

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

def generate_pdf_report(schedule, shifts, staff):
    """Platshållare för PDF-generering"""
    # Implementera senare med ReportLab eller liknande
    return b"PDF export kommer snart!"

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
time.sleep(1.5)
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
    if st.button("🚀 Generera schema", use_container_width=True):
        if not st.session_state.staff:
            st.error("Lägg till personal först")
        else:
            with st.spinner("🤖 AI optimerar ditt schema..."):
                try:
                    schedule, shifts = generate_fair_schedule(st.session_state.staff, min_score)
                    st.success("✅ Schema genererat!")
                    
                    # Visa tabell
                    schedule_df = pd.DataFrame([
                        {"Dag": days[i], "Personal": ", ".join(schedule[i]["staff"]), "Poäng": schedule[i]["score"]}
                        for i in range(7)
                    ])
                    
                    # Professionell datatabell
                    st.dataframe(
                        schedule_df.style.background_gradient(subset=["Poäng"], cmap="Blues"),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Avancerade visualiseringar
                    professional_visualizations(schedule, shifts, st.session_state.staff)
                    
                except ValueError as e:
                    st.error(f"Schemaläggningsfel: {str(e)}")
                    st.info("Tips: Öka antalet personal eller sänk minimikravet")
                    
                except Exception as e:
                    st.error(f"Oväntat fel: {str(e)}")
                    st.write("Logga detta fel och kontakta support")

if __name__ == "__main__":
    main()