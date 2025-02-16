# pages/1_Chefsida.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import random
from datetime import datetime, timedelta
from itertools import combinations
import sqlite3

from database import get_employees, update_employee

# ---------- SIDOPPSETTNING ----------
def setup_page():
    """Konfigurerar Streamlit-sidan."""
    st.set_page_config(page_title="Chefsida", layout="wide")

setup_page()

# ---------- KONFIGURATION ----------
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

# ---------- INITIERING AV SESSION ----------
def init_session():
    """Initialiserar sessionen med nödvändiga nycklar."""
    required_keys = [
        "staff", "dark_mode", "language", "user_type", "hospital", "min_experience_req",
        "period_start", "period_length",
        "morning_start", "morning_end", "em_start", "em_end", "night_start", "night_end",
        "team_size"
    ]
    defaults = {
        "staff": [],
        "dark_mode": False,
        "language": "sv",
        "user_type": "chef",
        "hospital": "Karolinska",
        "min_experience_req": 10,        # Minsta totala erfarenhetspoäng per pass
        "period_start": datetime(2025, 2, 16).date(),
        "period_length": 60,             # Schemaläggningsperiod i dagar
        "morning_start": "06:00",
        "morning_end": "14:00",
        "em_start": "14:00",
        "em_end": "22:00",
        "night_start": "22:00",
        "night_end": "06:00",
        "team_size": 3                   # Standardantal anställda per pass
    }
    for key in required_keys:
        if key not in st.session_state:
            st.session_state[key] = defaults[key]

init_session()

# ---------- HJÄLPFUNKTIONER ----------
def get_initials(name):
    """Returnerar initialer från ett namn."""
    parts = name.split()
    return "".join(p[0].upper() for p in parts if p)

def remove_employee(employee_id):
    """Tar bort en anställd från databasen via database.py."""
    try:
        from database import delete_employee  # Se till att delete_employee() finns i database.py
        delete_employee(employee_id)
        st.success("Anställd togs bort.")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Fel vid borttagning: {str(e)}")

# ---------- FUNKTIONER FÖR DAGSBASERAD SCHEMAGENERERING ----------
def can_work(emp, day, emp_state, shift_type):
    """
    Kontrollerar om en anställd kan arbeta på given dag.
    MAX ett pass per dag gäller, oavsett skifttyp.
    Kontrollerar även att max_shifts och max_consec_days inte överskrids.
    """
    state = emp_state[emp["id"]]
    if day in state["assigned_days"]:
        return (False, f"{emp['name']} är redan schemalagd den dagen.")
    if state["worked_shifts"] >= emp["max_shifts"]:
        return (False, f"{emp['name']} har nått max antal pass ({emp['max_shifts']}).")
    if state["last_worked_date"] is not None:
        delta = (day - state["last_worked_date"]).days
        if delta == 1 and state["consec_days"] + 1 > emp["max_consec_days"]:
            return (False, f"{emp['name']} överskrider max sammanhängande dagar ({emp['max_consec_days']}).")
    return (True, "")

def assign_shifts_for_day_greedy(day, shifts, available, emp_state, min_exp_req, team_size):
    """
    Tilldelar pass för en given dag (för varje skift) med en greedy, load-balancerad strategi.
    För varje skift går vi igenom alla möjliga kombinationer (från de anställda i 'available')
    och väljer den med lägst total belastning (summan av redan tilldelade pass).
    Returnerar en lista med tuples (shift, team) där team kan vara None om passet inte kan fyllas.
    Uppdaterar även emp_state.
    """
    assignments = []
    # Slumpa ordningen på available för att undvika alltid samma ordning
    random.shuffle(available)
    for shift in shifts:
        best_combo = None
        best_load = None
        for combo in combinations(available, team_size):
            total_exp = sum(emp["experience"] for emp in combo)
            if total_exp < min_exp_req:
                continue
            if not any(emp["experience"] >= 4 for emp in combo):
                continue
            valid = True
            for emp in combo:
                ok, _ = can_work(emp, day, emp_state, shift["shift"])
                if not ok:
                    valid = False
                    break
            if not valid:
                continue
            load = sum(emp_state[emp["id"]]["worked_shifts"] for emp in combo)
            if best_combo is None or load < best_load:
                best_combo = combo
                best_load = load
        if best_combo is not None:
            # Uppdatera emp_state för varje anställd i best_combo
            for emp in best_combo:
                state = emp_state[emp["id"]]
                state["worked_shifts"] += 1
                state["assigned_days"].add(day)
                if state["last_worked_date"] is not None and (day - state["last_worked_date"]).days == 1:
                    state["consec_days"] += 1
                else:
                    state["consec_days"] = 1
                state["last_worked_date"] = day
            assignments.append((shift, best_combo))
            # Ta bort de som fått passet från available (max ett pass per dag)
            available = [emp for emp in available if emp not in best_combo]
        else:
            assignments.append((shift, None))
    return assignments, emp_state

# ---------- HUVUDFUNKTION FÖR SCHEMAGENERERING ----------
def generate_schedule(employees: list[tuple]) -> None:
    """
    Schemalägger tre skift per dag över en period (exempelvis två månader).
    Varje pass (skift) ska ha:
      - Total erfarenhet ≥ chefens krav (min_exp_req)
      - Minst en anställd med erfarenhet ≥ 4
    Varje anställd får högst ett pass per dag.
    """
    # Hämta inställningar
    period_start = st.session_state["period_start"]
    period_length = st.session_state["period_length"]
    min_exp_req = st.session_state["min_experience_req"]
    team_size = st.session_state["team_size"]

    morning_start = st.session_state["morning_start"]
    morning_end = st.session_state["morning_end"]
    em_start = st.session_state["em_start"]
    em_end = st.session_state["em_end"]
    night_start = st.session_state["night_start"]
    night_end = st.session_state["night_end"]

    shift_types = [
        {"shift": "Morgon", "start": morning_start, "end": morning_end},
        {"shift": "EM", "start": em_start, "end": em_end},
        {"shift": "Natt", "start": night_start, "end": night_end}
    ]

    dates = [period_start + timedelta(days=i) for i in range(period_length)]
    daily_shifts = {}
    for d in dates:
        weekday = d.strftime("%A")
        daily_shifts[d] = []
        for stype in shift_types:
            daily_shifts[d].append({
                "date": d,
                "day": weekday,
                "shift": stype["shift"],
                "start": stype["start"],
                "end": stype["end"]
            })

    # Konvertera anställdas data till dictionaries
    new_staff = []
    for e in employees:
        try:
            exp_val = int(e[7])
        except:
            exp_val = 0
        base_max = round((e[3] / 100) * period_length)
        if base_max < 1:
            base_max = 1
        new_staff.append({
            "id": e[0],
            "name": e[2],
            "workload_percent": e[3],
            "work_types": e[4].split(",") if e[4] else [],
            "max_consec_days": e[5],
            "min_days_off": e[6],
            "experience": exp_val,
            "max_shifts": base_max
        })
        
    if not any(s["experience"] >= 4 for s in new_staff):
        st.error("Konflikt: Det måste finnas minst en anställd med erfarenhet 4 eller högre.")
        return

    # Initiera anställdastatus (emp_state)
    emp_state = {}
    for s in new_staff:
        emp_state[s["id"]] = {
            "worked_shifts": 0,
            "last_worked_date": None,
            "consec_days": 0,
            "assigned_days": set()
        }

    schedule = []
    failed_days = {}
    # Processa dag för dag
    for day in dates:
        available_day = new_staff.copy()
        # Slumpa ordningen för rätt variation
        random.shuffle(available_day)
        shifts = daily_shifts[day]
        assignments, emp_state = assign_shifts_for_day_greedy(day, shifts, available_day, emp_state, min_exp_req, team_size)
        for shift, team in assignments:
            if team is None:
                if day not in failed_days:
                    failed_days[day] = []
                failed_days[day].append(f"{shift['shift']}: Ingen kombination uppfyllde kraven (minsta total erfarenhet {min_exp_req} samt minst en med ≥4).")
            schedule.append({"slot": shift, "assigned": team})
    
    if failed_days:
        error_msgs = []
        for d, msgs in failed_days.items():
            for m in msgs:
                error_msgs.append(f"{d} ({m})")
        st.error("Följande pass kunde inte schemaläggas:\n" + "\n".join(error_msgs))
    
    # Bygg schemaöversiktstabell
    schedule_rows = []
    for item in schedule:
        slot = item["slot"]
        team = item["assigned"]
        if team is None:
            initials = "–"
        else:
            initials = ", ".join(get_initials(emp["name"]) for emp in team)
        schedule_rows.append({
            "Datum": slot["date"].strftime("%Y-%m-%d"),
            "Veckodag": slot["day"],
            "Skift": slot["shift"],
            "Tid": f"{slot['start']} - {slot['end']}",
            "Personal (Initialer)": initials
        })
    schedule_df = pd.DataFrame(schedule_rows)
    
    summary_rows = []
    for emp in new_staff:
        summary_rows.append({
            "Namn": emp["name"],
            "Pass": emp_state[emp["id"]]["worked_shifts"]
        })
    summary_df = pd.DataFrame(summary_rows).sort_values("Namn")
    
    st.subheader("Schemalagd översikt")
    st.dataframe(schedule_df, use_container_width=True)
    
    st.subheader("Översikt: Antal pass per anställd")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    # Kalenderöversikt (pivot-tabell)
    fig, ax = plt.subplots(figsize=(12, 6))
    try:
        pivot = schedule_df.pivot(index="Datum", columns="Skift", values="Personal (Initialer)")
    except Exception:
        pivot = pd.DataFrame()
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=pivot.fillna("").values,
                     colLabels=pivot.columns,
                     rowLabels=pivot.index,
                     loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    ax.set_title("Kalenderöversikt för kommande pass")
    st.pyplot(fig)

def show_chef_interface_wrapper():
    init_session()
    lang = LANGUAGES["sv"]
    st.title(f"👨💼 Chefssida - {st.session_state.hospital}")
    st.markdown("---")
    
    # --- Ta bort anställd ---
    st.subheader("Hantera anställda")
    employees = get_employees(st.session_state.hospital)
    if employees:
        emp_options = {f"{e[2]} (ID: {e[0]})": e[0] for e in employees}
        to_delete = st.selectbox("Välj anställd att ta bort", options=list(emp_options.keys()))
        if st.button("Ta bort anställd"):
            delete_id = emp_options[to_delete]
            remove_employee(delete_id)
            st.experimental_rerun()
    else:
        st.info("Inga anställda finns att hantera.")
    
    st.markdown("---")
    # --- Personalhantering (Redigera) ---
    st.header("👥 Personalhantering")
    if not employees:
        st.warning("Inga anställda registrerade ännu.")
    else:
        emp_options = [f"{e[2]} (ID: {e[0]})" for e in employees]
        selected_emp = st.selectbox("Välj anställd att redigera", emp_options)
        emp_id = int(selected_emp.split("ID: ")[1].replace(")", "")) if selected_emp else None
        if emp_id:
            emp_data = next(e for e in employees if e[0] == emp_id)
            with st.form(key="edit_employee"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Namn", value=emp_data[2])
                    new_workload = st.slider("Arbetsbelastning (%)", 50, 100, emp_data[3], step=5)
                    current_exp = emp_data[7] if emp_data[7] else 1
                    exp_index = max(0, int(current_exp) - 1)
                    new_exp = st.selectbox("Erfarenhetsnivå", options=list(lang["experience_labels"].keys()),
                                            index=exp_index,
                                            format_func=lambda x: lang["experience_labels"][x])
                with col2:
                    work_types = st.multiselect("Arbetsformer",
                                                ["Nattjour", "Dagskift", "Kvällsskift", "Helg", "Administration"],
                                                default=emp_data[4].split(",") if emp_data[4] else [])
                    max_days = st.number_input("Max sammanhängande dagar", min_value=1, max_value=7, value=emp_data[5])
                    min_off = st.number_input("Minsta lediga dagar", min_value=1, max_value=3, value=emp_data[6])
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
                    except Exception as e:
                        st.error(f"Fel vid uppdatering av anställd: {str(e)}")
    
    st.markdown("---")
    # --- Inställningar för schemagenerering ---
    st.subheader("Schemainställningar")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        period_start = st.date_input("Startdatum", value=datetime(2025, 2, 16).date())
        st.session_state["period_start"] = period_start
    with col2:
        period_length = st.number_input("Antal dagar att schemalägga", min_value=7, max_value=90, value=60)
        st.session_state["period_length"] = period_length
    with col3:
        st.session_state["min_experience_req"] = st.slider("Minsta totala erfarenhetspoäng per pass",
                                                            min_value=5, max_value=50,
                                                            value=st.session_state.get("min_experience_req", 10),
                                                            step=1)
    with col4:
        st.session_state["team_size"] = st.slider("Antal anställda per pass",
                                                  min_value=1, max_value=10,
                                                  value=st.session_state.get("team_size", 3),
                                                  step=1)
    st.markdown("### Skiftinställningar")
    col1, col2, col3 = st.columns(3)
    with col1:
        morning_start = st.time_input("Morgonpass start", value=datetime.strptime("06:00", "%H:%M").time())
        st.session_state["morning_start"] = morning_start.strftime("%H:%M")
    with col2:
        morning_end = st.time_input("Morgonpass slut", value=datetime.strptime("14:00", "%H:%M").time())
        st.session_state["morning_end"] = morning_end.strftime("%H:%M")
    with col3:
        em_start = st.time_input("EM-pass start", value=datetime.strptime("14:00", "%H:%M").time())
        st.session_state["em_start"] = em_start.strftime("%H:%M")
    col1, col2 = st.columns(2)
    with col1:
        em_end = st.time_input("EM-pass slut", value=datetime.strptime("22:00", "%H:%M").time())
        st.session_state["em_end"] = em_end.strftime("%H:%M")
    with col2:
        night_start = st.time_input("Nattpass start", value=datetime.strptime("22:00", "%H:%M").time())
        st.session_state["night_start"] = night_start.strftime("%H:%M")
    night_end = st.time_input("Nattpass slut", value=datetime.strptime("06:00", "%H:%M").time())
    st.session_state["night_end"] = night_end.strftime("%H:%M")
    
    st.markdown("---")
    if st.button("🚀 Generera schema"):
        generate_schedule(employees)
    
    st.markdown("---")
    if st.button("🚪 Logga ut"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.markdown("<meta http-equiv='refresh' content='0; url=https://vardschema.streamlit.app/' />",
                    unsafe_allow_html=True)
        st.stop()

# ---------- Start ----------
show_chef_interface_wrapper()
