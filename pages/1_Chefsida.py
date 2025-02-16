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
    """Set up the Streamlit page configuration."""
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

# Teamstorlek per pass
TEAM_SIZE = 3

# ---------- INITIERING AV SESSION ----------
def init_session():
    """Initialize session state med nödvändiga nycklar."""
    required_keys = [
        "staff", "dark_mode", "language", "user_type", "hospital", "min_experience_req",
        "period_start", "period_length",
        "morning_start", "morning_end", "em_start", "em_end", "night_start", "night_end"
    ]
    defaults = {
        "staff": [],
        "dark_mode": False,
        "language": "sv",
        "user_type": "chef",
        "hospital": "Karolinska",
        "min_experience_req": 10,  # Minsta total erfarenhetspoäng per pass
        "period_start": datetime(2025, 2, 16).date(),
        "period_length": 60,       # Schemaläggningsperiod i dagar
        "morning_start": "06:00",
        "morning_end": "14:00",
        "em_start": "14:00",
        "em_end": "22:00",
        "night_start": "22:00",
        "night_end": "06:00"
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

# Funktion för att ta bort en anställd från databasen
def remove_employee(employee_id):
    try:
        from database import delete_employee  # Importera delete_employee från database.py
        delete_employee(employee_id)
        st.success("Anställd togs bort.")
        # Om du vill att sidan ska ladda om automatiskt, försök med st.experimental_rerun().
        # Om det orsakar problem, kommentera ut nästa rad.
        ## st.experimental_rerun()
    except Exception as e:
        st.error(f"Fel vid borttagning: {str(e)}")


# ---------- FUNKTIONER FÖR DAGSBASERAD SCHEMAGENERERING ----------
def can_work(emp, day, emp_state):
    """
    Kollar om en anställd kan arbeta på given dag.
    Inga två pass per dag är tillåtna.
    Kontrollerar också att max_shifts och max_consec_days inte överskrids.
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

def assign_shifts_for_day(day, shifts, available, emp_state, min_exp_req):
    """
    Backtracking-funktion för att dela in tillgänglig personal (available)
    i TEAM_SIZE-grupper för samtliga shifts under en dag.
    Returnerar (assignment, updated_emp_state) eller None om det inte går.
    assignment är en lista med tuples (shift, team)
    """
    if not shifts:
        return ([], emp_state)
    current_shift = shifts[0]
    # Prova alla kombinationer av TEAM_SIZE från available
    for combo in combinations(available, TEAM_SIZE):
        total_exp = sum(emp["experience"] for emp in combo)
        if total_exp < min_exp_req:
            continue
        if not any(emp["experience"] >= 4 for emp in combo):
            continue
        valid = True
        for emp in combo:
            ok, _ = can_work(emp, day, emp_state)
            if not ok:
                valid = False
                break
        if not valid:
            continue
        # Gör en kopia av emp_state och uppdatera för de anställda i combo
        new_state = {eid: emp_state[eid].copy() for eid in emp_state}
        for emp in combo:
            s = new_state[emp["id"]]
            s["worked_shifts"] += 1
            s["assigned_days"].add(day)
            if s["last_worked_date"] is not None and (day - s["last_worked_date"]).days == 1:
                s["consec_days"] += 1
            else:
                s["consec_days"] = 1
            s["last_worked_date"] = day
        remaining_available = [emp for emp in available if emp not in combo]
        result = assign_shifts_for_day(day, shifts[1:], remaining_available, new_state, min_exp_req)
        if result is not None:
            assignment_rest, final_state = result
            return ([(current_shift, combo)] + assignment_rest, final_state)
    return None

# ---------- HUVUDFUNKTION FÖR SCHEMAGENERERING ----------
def generate_schedule(employees: list[tuple]) -> None:
    """
    Schemalägg tre skift per dag över en period (exempelvis två månader).
    Varje pass (shift) ska ha:
      - Total erfarenhet >= chefens krav (min_exp_req)
      - Minst en anställd med erfarenhet ≥4
    Varje anställd får högst ett pass per dag.
    """
    # Hämta inställningar
    period_start = st.session_state["period_start"]
    period_length = st.session_state["period_length"]
    min_exp_req = st.session_state["min_experience_req"]

    morning_start = st.session_state["morning_start"]
    morning_end = st.session_state["morning_end"]
    em_start = st.session_state["em_start"]
    em_end = st.session_state["em_end"]
    night_start = st.session_state["night_start"]
    night_end = st.session_state["night_end"]

    # Definiera shifts
    shift_types = [
        {"shift": "Morgon", "start": morning_start, "end": morning_end},
        {"shift": "EM", "start": em_start, "end": em_end},
        {"shift": "Natt", "start": night_start, "end": night_end}
    ]

    # Skapa lista med datum för perioden
    dates = [period_start + timedelta(days=i) for i in range(period_length)]
    
    # För varje dag, skapa shift-pass (alla tre skift)
    daily_shifts = {}  # key: datum, value: list av shift-dikter
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
        # Här används base_max direkt som max_shifts (eventuella ytterligare regler kan läggas till)
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
        
    schedule = []    # Lista med schemauppgifter (per shift)
    failed_days = {} # Datum -> lista med felmeddelanden för de shifts som ej kunde fyllas

    # Processa dag för dag (alla shifts per dag)
    for day in dates:
        shifts = daily_shifts[day]
        res = assign_shifts_for_day(day, shifts, new_staff, emp_state, min_exp_req)
        if res is None:
            # Om vi inte hittar en fullständig lösning för dagen, markera alla shifts som ej schemalagda
            failed_days[day] = [f"{shift['shift']}: Ingen kombination uppfyllde kraven (minst total erfarenhet {min_exp_req} samt minst en med ≥4)." for shift in shifts]
            # Lägg in tomma poster i schemat
            for shift in shifts:
                schedule.append({"slot": shift, "assigned": None})
        else:
            assignment, updated_state = res
            emp_state = updated_state  # Uppdatera global state
            for asg in assignment:
                shift_info, team = asg
                schedule.append({"slot": shift_info, "assigned": team})
    
    # Om det fanns fel, visa en varning
    if failed_days:
        error_msgs = []
        for d, msgs in failed_days.items():
            for m in msgs:
                error_msgs.append(f"{d} ({m})")
        st.error("Följande pass kunde inte schemaläggas:\n" + "\n".join(error_msgs))
    
    # Bygg schemaöversikt (tabell)
    schedule_rows = []
    for item in schedule:
        slot = item["slot"]
        assigned = item["assigned"]
        if assigned is None:
            initials = "–"
        else:
            initials = ", ".join(get_initials(emp["name"]) for emp in assigned)
        schedule_rows.append({
            "Datum": slot["date"].strftime("%Y-%m-%d"),
            "Veckodag": slot["day"],
            "Skift": slot["shift"],
            "Tid": f"{slot['start']} - {slot['end']}",
            "Personal (Initialer)": initials
        })
    schedule_df = pd.DataFrame(schedule_rows)
    
    # Sammanfattning: antal pass per anställd
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

# ---------- CHEFSSIDANS GRÄNSSNITT ----------
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
           # st.experimental_rerun() 
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
                       # st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Fel vid uppdatering av anställd: {str(e)}")
    
    st.markdown("---")
    # --- Inställningar för schemagenerering ---
    st.subheader("Schemainställningar")
    col1, col2, col3 = st.columns(3)
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
