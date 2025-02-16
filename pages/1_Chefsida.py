# pages/1_Chefsida.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import random
from datetime import datetime
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
    required_keys = [
        "staff", "dark_mode", "language", "user_type", "hospital", "min_experience_req"
    ]
    defaults = {
        "staff": [],
        "dark_mode": False,
        "language": "sv",
        "user_type": "chef",
        "hospital": "Karolinska",
        "min_experience_req": 10  # Defaultvärde för minsta totala erfarenhetspoäng per dag
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
                    current_exp = emp_data[7] if emp_data[7] else 1
                    exp_index = max(0, int(current_exp) - 1)
                    new_exp = st.selectbox(
                        "Erfarenhetsnivå",
                        options=list(lang["experience_labels"].keys()),
                        index=exp_index,
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
                        st.stop()  # Förhindra dubbelkörning
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
    # Slider för minsta totala erfarenhetspoäng per dag (chefens krav)
    st.subheader("Inställningar för schemagenerering")
    min_exp_req = st.slider(
        "Minsta totala erfarenhetspoäng per dag",
        min_value=5,
        max_value=50,
        value=st.session_state["min_experience_req"],
        step=1
    )
    st.session_state["min_experience_req"] = min_exp_req

    # Schemagenerering
    st.header("📅 Schemagenerering")
    if st.button("🚀 Generera schema"):
        generate_schedule(employees)
    
    st.markdown("---")
    # Utloggningsknapp – rensar sessionen och omdirigerar
    if st.button("🚪 Logga ut"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.markdown(
            "<meta http-equiv='refresh' content='0; url=https://vardschema.streamlit.app/' />",
            unsafe_allow_html=True
        )
        st.stop()

# ---------- Hjälpfunktion för individrestriktioner ----------
def can_work_with_reason(emp, day_idx, staff_state):
    """
    Returnerar en tuple (bool, reason) som anger om emp kan arbeta på day_idx.
    Här kontrolleras att inte max_work_days eller max_consec_days överskrids.
    """
    st_state = staff_state[emp["id"]]
    if st_state["worked_days"] >= emp["max_work_days"]:
        return (False, f"{emp['name']} har nått max arbetsdagar ({emp['max_work_days']}).")
    potential_consec = 1
    if day_idx == st_state["last_worked_day"] + 1:
        potential_consec = st_state["consec_days"] + 1
    if potential_consec > emp["max_consec_days"]:
        return (False, f"{emp['name']} överskrider max sammanhängande dagar ({emp['max_consec_days']}).")
    return (True, "")

# ========== SCHEMAGENERERING (ADVANCED) ==========
def generate_schedule(employees: list[tuple]) -> None:
    """
    Generera schema för 7 dagar (Mån-Sön) baserat på anställdas data.
    Tar hänsyn till:
      - Minst en med experience >= 4 per dag
      - max_consec_days
      - Arbetsbelastning i % (workload) → max antal arbetsdagar av 7
      - Minsta totala erfarenhetspoäng (chefens krav)
    Använder en backtracking-algoritm.
    """
    days = LANGUAGES["sv"]["days"]
    min_exp_req = st.session_state.get("min_experience_req", 10)

    # Konvertera anställdas data till en lista med dictionaries.
    # Vi räknar ut baserat på arbetsbelastning, men begränsar även så att antalet arbetsdagar
    # inte överstiger (7 - min_days_off) för att säkerställa att minsta lediga dagar respekteras.
    staff = []
    for e in employees:
        base_max = round((e[3] / 100) * 7)
        if base_max < 1:
            base_max = 1
        # Effektivt max: man får inte arbeta mer än (7 - min_days_off) dagar under veckan.
        effective_max = min(base_max, 7 - e[6])
        try:
            exp_val = int(e[7])
        except:
            exp_val = 0
        staff.append({
            "id": e[0],
            "name": e[2],
            "workload_percent": e[3],
            "work_types": e[4].split(",") if e[4] else [],
            "max_consec_days": e[5],
            "min_days_off": e[6],  # Behåll för historik, men används ej i per-dag-check längre.
            "experience": exp_val,
            "max_work_days": effective_max
        })

    if not any(s["experience"] >= 4 for s in staff):
        st.error("Konflikt: Det måste finnas minst en anställd med erfarenhet 4 eller högre.")
        return

    final_assignment = [None] * len(days)
    staff_state = {}
    for s in staff:
        staff_state[s["id"]] = {
            "worked_days": 0,
            "consec_days": 0,
            "last_worked_day": -999
        }

    # Variabler för att spåra varför schemaläggningen misslyckas
    st.session_state["failed_day"] = None
    st.session_state["fail_reason"] = ""

    def backtrack(day_idx):
        if day_idx == len(days):
            return True

        combo_list = list(combinations(staff, TEAM_SIZE))
        random.shuffle(combo_list)
        feasible_combo_found = False

        for combo in combo_list:
            # Kontrollera att minst en har erfarenhet >= 4
            if not any(e["experience"] >= 4 for e in combo):
                continue
            # Kontrollera total erfarenhet
            total_exp = sum(e["experience"] for e in combo)
            if total_exp < min_exp_req:
                continue
            # Kontrollera individuella restriktioner
            individual_ok = True
            for e in combo:
                ok, _ = can_work_with_reason(e, day_idx, staff_state)
                if not ok:
                    individual_ok = False
                    break
            if not individual_ok:
                continue

            # Om vi når hit är kombinationen genomförbar
            feasible_combo_found = True
            saved_states = {}
            for e in combo:
                saved_states[e["id"]] = staff_state[e["id"]].copy()
                if day_idx == staff_state[e["id"]]["last_worked_day"] + 1:
                    staff_state[e["id"]]["consec_days"] += 1
                else:
                    staff_state[e["id"]]["consec_days"] = 1
                staff_state[e["id"]]["worked_days"] += 1
                staff_state[e["id"]]["last_worked_day"] = day_idx

            final_assignment[day_idx] = combo

            if backtrack(day_idx + 1):
                return True
            else:
                for e in combo:
                    staff_state[e["id"]] = saved_states[e["id"]]
        if not feasible_combo_found:
            # Bestäm vilka constraint-grupper som misslyckades
            leader_ok = any(any(e["experience"] >= 4 for e in combo) for combo in combo_list)
            total_exp_ok = any(
                any(e["experience"] >= 4 for e in combo) and sum(e["experience"] for e in combo) >= min_exp_req
                for combo in combo_list
            )
            individual_ok = any(
                any(e["experience"] >= 4 for e in combo) and 
                sum(e["experience"] for e in combo) >= min_exp_req and
                all(can_work_with_reason(e, day_idx, staff_state)[0] for e in combo)
                for combo in combo_list
            )
            failed_constraints = []
            if not leader_ok:
                failed_constraints.append("minst en med erfarenhet >= 4")
            if not total_exp_ok:
                failed_constraints.append(f"total erfarenhet (krav {min_exp_req})")
            if not individual_ok:
                failed_constraints.append("individuella restriktioner (max_consec_days, max_work_days)")
            st.session_state["failed_day"] = day_idx
            st.session_state["fail_reason"] = ", ".join(failed_constraints)
        return False

    found_solution = backtrack(0)

    if not found_solution:
        fail_day = st.session_state.get("failed_day", None)
        fail_reason = st.session_state.get("fail_reason", "Okänt skäl")
        if fail_day is not None:
            st.error(
                f"Kunde inte hitta ett giltigt schema. Det gick inte att schemalägga {days[fail_day]} eftersom följande constraint(s) inte uppfylldes: {fail_reason}."
            )
        else:
            st.error("Kunde inte hitta ett giltigt schema givet alla constraints.")
        return

    # Bygg DataFrame av schemat
    schedule_rows = []
    for i, combo in enumerate(final_assignment):
        day_name = days[i]
        names = [emp["name"] for emp in combo]
        total_exp = sum(emp["experience"] for emp in combo)
        leaders = [emp["name"] for emp in combo if emp["experience"] >= 4]
        schedule_rows.append({
            "Dag": day_name,
            "Personal": ", ".join(names),
            "Ledare": ", ".join(leaders),
            "Poäng": total_exp
        })

    schedule_df = pd.DataFrame(schedule_rows)
    st.dataframe(
        schedule_df.style.background_gradient(subset=["Poäng"], cmap="YlGnBu"),
        hide_index=True,
        use_container_width=True
    )
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

# Anropa chefsidans gränssnitt
show_chef_interface()
