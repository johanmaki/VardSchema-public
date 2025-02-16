# pages/1_Chefsida.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import math
from itertools import combinations

from database import get_employees, update_employee

# Function to set up page configuration
def setup_page():
    """Set up the Streamlit page configuration."""
    st.set_page_config(page_title="Chefsida", layout="wide")

# Call the setup function
setup_page()

# ========== KONFIGURATION ==========
THEME_COLORS = {
    "light": {"primary": "#1E88E5", "secondary": "#FF6D00"},
    "dark": {"primary": "#90CAF9", "secondary": "#FFAB40"}
}

LANGUAGES = {
    "sv": {
        "title": "AI-drivet Schemaläggningssystem",
        "days": ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"],
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

# Antal personer vi vill schemalägga per dag (kan justeras)
TEAM_SIZE = 3

# ========== INITIERING AV SESSION ==========
def init_session():
    """Initialize session state with required keys."""
    required_keys = ["staff", "dark_mode", "language", "user_type", "hospital"]
    defaults = {
        "staff": [],
        "dark_mode": False,
        "language": "sv",
        "user_type": "chef",
        "hospital": "Karolinska"
    }
    for key in required_keys:
        if key not in st.session_state:
            st.session_state[key] = defaults[key]

# ========== CHEFSGRÄNSSNITT ==========
def show_chef_interface():
    """Display the chef interface."""
    init_session()
    lang = LANGUAGES["sv"]
    
    # Header
    st.title(f"👨💼 Chefssida - {st.session_state.hospital}")
    st.markdown("---")
    
    # Hämta personal från databasen
    employees = get_employees(st.session_state.hospital)
    
    st.header("👥 Personalhantering")
    
    if not employees:
        st.warning("Inga anställda registrerade ännu.")
    else:
        # Välj anställd att redigera
        emp_options = [f"{e[2]} (ID: {e[0]})" for e in employees]
        selected_emp = st.selectbox("Välj anställd", emp_options)
        emp_id = int(selected_emp.split("ID: ")[1].replace(")", "")) if selected_emp else None

        if emp_id:
            emp_data = next(e for e in employees if e[0] == emp_id)
            
            with st.form(key="edit_employee"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_name = st.text_input("Namn", value=emp_data[2])
                    new_workload = st.slider(
                        "Arbetsbelastning (%)",
                        50, 100, emp_data[3], step=5
                    )
                    new_exp = st.selectbox(
                        "Erfarenhetsnivå",
                        options=list(lang["experience_labels"].keys()),
                        index=emp_data[7]-1,
                        format_func=lambda x: lang["experience_labels"][x]
                    )
                    
                with col2:
                    work_types = st.multiselect(
                        "Arbetsformer",
                        ["Nattjour", "Dagskift", "Kvällsskift", "Helg", "Administration"],
                        default=emp_data[4].split(",") if emp_data[4] else []
                    )
                    max_days = st.number_input(
                        "Max sammanhängande dagar",
                        min_value=1, max_value=7, 
                        value=emp_data[5]
                    )
                    min_off = st.number_input(
                        "Minsta lediga dagar",
                        min_value=1, max_value=3,
                        value=emp_data[6]
                    )
                
                if st.form_submit_button("💾 Spara ändringar"):
                    update_data = {
                        "id": emp_id,
                        "workload": new_workload,
                        "work_types": work_types,
                        "max_consec_days": max_days,
                        "min_days_off": min_off,
                        "experience": new_exp
                    }
                    try:
                        update_employee(update_data)
                        st.success("Ändringar sparade!")
                        st.stop()  # Stop execution to prevent double-run
                    except Exception as e:
                        st.error(f"Fel vid uppdatering av anställd: {str(e)}")
    
    st.markdown("---")
    # Informationsknapp för erfarenhetsnivåer
    if st.button("ℹ️ Vad betyder erfarenhetsnivåerna?"):
        st.info(
            f"""
            **Erfarenhetsnivåer:**
            - **1 - Nyexaminerad:** Ingen eller minimal erfarenhet.
            - **2 - Grundläggande:** Har viss grundläggande erfarenhet, men behöver mycket handledning.
            - **3 - Erfaren:** Klarar de flesta arbetsuppgifter självständigt.
            - **4 - Mycket erfaren:** Kan hantera komplexa uppgifter och axla ledningsansvar.
            - **5 - Expert:** Har djupgående kunskaper och kan agera som mentor.
            - **6 - Avdelningsansvarig:** Leder teamet och tar strategiska beslut.
            """
        )
    
    st.markdown("---")
    # Schemagenerering
    st.header("📅 Schemagenerering")
    if st.button("🚀 Generera schema"):
        generate_schedule(employees)
    
    st.markdown("---")
    # Utloggningsknapp – rensar sessionen och omdirigerar till startsidan (inloggningssidan)
    if st.button("🚪 Logga ut"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.markdown(
            "<meta http-equiv='refresh' content='0; url=https://vardschema.streamlit.app/' />",
            unsafe_allow_html=True
        )
        st.stop()

# ========== SCHEMAGENERERING (ADVANCED) ==========
def generate_schedule(employees: list[tuple]) -> None:
    """
    Generera schema för 7 dagar (Mån-Sön) baserat på anställdas data.
    Tar hänsyn till:
      - Minst en med experience >= 4 per dag
      - max_consec_days
      - min_days_off
      - Arbetsbelastning i % (workload) -> max antal arbetsdagar av 7
    Använder en backtracking-algoritm.
    """

    # 1) Konvertera anställdas data till en lista med dictionaries
    staff = []
    for e in employees:
        # Beräkna max tillåtna arbetsdagar (avrundat)
        max_work_days = round((e[3] / 100) * 7)  # e[3] = workload i %
        if max_work_days < 1:
            max_work_days = 1  # Se till att minst 1 dag är möjlig om workload >= 50

        staff.append({
            "id": e[0],
            "name": e[2],
            "workload_percent": e[3],
            "work_types": e[4].split(",") if e[4] else [],
            "max_consec_days": e[5],
            "min_days_off": e[6],
            "experience": int(e[7]) if isinstance(e[7], (int, str)) and str(e[7]).isdigit() else 0,
            "max_work_days": max_work_days
        })

    days = LANGUAGES["sv"]["days"]  # ["Måndag", "Tisdag", ... "Söndag"]

    # Kontroll: finns åtminstone en med experience >= 4 totalt?
    if not any(s["experience"] >= 4 for s in staff):
        st.error("Konflikt: Det måste finnas minst en anställd med erfarenhet 4 eller högre.")
        return

    # Här lagrar vi det slutliga schemat om vi hittar en lösning
    final_assignment = [None] * len(days)  # Varje index blir en lista av anställda

    # State: info om varje anställd under backtracking
    # (hur många dagar jobbat totalt, hur många dagar i rad, senaste dag man jobbade)
    staff_state = {}
    for s in staff:
        staff_state[s["id"]] = {
            "worked_days": 0,
            "consec_days": 0,
            "last_worked_day": -999  # inget datum
        }

    # En hjälp-funktion för att kolla om en anställd kan jobba en viss dag
    def can_work(emp, day_idx):
        """
        Kollar om 'emp' kan schemaläggas day_idx givet staff_state + constraints.
        """
        st_state = staff_state[emp["id"]]

        # Har personen redan nått sitt max antal arbetsdagar?
        if st_state["worked_days"] >= emp["max_work_days"]:
            return False

        # Om de jobbade igår (day_idx - 1 == last_worked_day), checka max_consec_days
        # Om de inte jobbade igår, nollställs consecutive days när vi lägger in dem igen.
        # MEN vi måste också checka min_days_off.
        days_since_worked = day_idx - st_state["last_worked_day"] - 1

        # Kolla om de inte har haft tillräcklig vila
        if days_since_worked < emp["min_days_off"]:
            return False

        # Kolla om de redan jobbat X dagar i rad och inte haft vila
        # Om de jobbade igår => consecutive = st_state["consec_days"] + 1
        # Om de inte jobbade igår => consecutive = 1
        # Men vi kan inte bara kolla st_state["consec_days"], för den nollställs först
        # när de faktiskt är lediga en dag. Se logik i assign() nedan.

        # Prova hur många i rad det skulle bli om vi sätter dem idag:
        potential_consec = 1
        if day_idx == st_state["last_worked_day"] + 1:
            # då fortsätter de i rad
            potential_consec = st_state["consec_days"] + 1

        if potential_consec > emp["max_consec_days"]:
            return False

        return True

    # Funktionen som "lägger in" en anställd i schemat för day_idx och uppdaterar staff_state
    def assign_employee(emp, day_idx):
        """Uppdatera staff_state när en anställd emp läggs in på day_idx."""
        st_state = staff_state[emp["id"]]
        # Räkna ut om vi fortsätter i rad eller inte
        if day_idx == st_state["last_worked_day"] + 1:
            st_state["consec_days"] += 1
        else:
            st_state["consec_days"] = 1  # startar en ny kedja

        st_state["worked_days"] += 1
        st_state["last_worked_day"] = day_idx

    # Funktionen som "tar bort" en anställd från day_idx (backtrack) och återställer staff_state
    def unassign_employee(emp, prev_state):
        """Återställ staff_state när vi backar."""
        staff_state[emp["id"]] = prev_state

    # Backtracking-funktion
    def backtrack(day_idx):
        """Försök fylla dag day_idx. Om vi kommer förbi sista dagen -> True (klar)."""
        if day_idx == len(days):
            return True  # alla dagar klara

        # Vi vill välja TEAM_SIZE anställda för day_idx.
        # Constraint: minst 1 med experience >= 4
        possible_combos = combinations(staff, TEAM_SIZE)

        for combo in possible_combos:
            # Kolla om minst en har experience >= 4
            if not any(e["experience"] >= 4 for e in combo):
                continue

            # Kolla om alla i combo är "can_work" day_idx
            # och att de inte krockar med varandra på något sätt
            # (i detta exempel antar vi att krockar ej finns om de uppfyller individuella constraints)
            feasible = True
            saved_states = {}
            for e in combo:
                if not can_work(e, day_idx):
                    feasible = False
                    break

            if not feasible:
                continue

            # Om det är genomförbart, "lägg in" dem
            for e in combo:
                saved_states[e["id"]] = staff_state[e["id"]].copy()  # spara för unassign
                assign_employee(e, day_idx)

            # Sätt final_assignment
            final_assignment[day_idx] = combo

            # Fortsätt till nästa dag
            if backtrack(day_idx + 1):
                return True
            else:
                # Backa (unassign)
                for e in combo:
                    unassign_employee(e, saved_states[e["id"]])

        return False

    # Kör backtracking
    found_solution = backtrack(0)

    if not found_solution:
        st.error("Kunde inte hitta ett giltigt schema givet alla constraints.")
        return

    # Bygg DataFrame av final_assignment
    schedule_rows = []
    for i, combo in enumerate(final_assignment):
        day_name = days[i]
        # Samma "combo" är en tuple av anställda
        names = [emp["name"] for emp in combo]
        total_exp = sum(emp["experience"] for emp in combo)
        # Markera ledare (minst en har >= 4, men vi kan t.ex. bara markera alla med >=4)
        leaders = [emp["name"] for emp in combo if emp["experience"] >= 4]

        schedule_rows.append({
            "Dag": day_name,
            "Personal": ", ".join(names),
            "Ledare": ", ".join(leaders),
            "Poäng": total_exp
        })

    schedule_df = pd.DataFrame(schedule_rows)

    # Visa schema
    st.dataframe(
        schedule_df.style.background_gradient(subset=["Poäng"], cmap="YlGnBu"),
        hide_index=True,
        use_container_width=True
    )

    # Visa stapeldiagram
    fig, ax = plt.subplots()
    x = range(len(schedule_df))
    ax.bar(
        x,
        schedule_df["Poäng"],
        color=THEME_COLORS["dark" if st.session_state.dark_mode else "light"]["primary"]
    )
    ax.set_xticks(x)
    ax.set_xticklabels(schedule_df["Dag"])
    ax.set_ylabel("Summa erfarenhetspoäng")
    ax.set_title("Erfarenhetspoäng per dag")
    st.pyplot(fig)

# Anropa chefsidans gränssnitt så att sidan renderas
show_chef_interface()
