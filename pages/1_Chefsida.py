# pages/1_Chefsida.py

import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
from itertools import combinations
from io import BytesIO  # För Excel-export

from database import get_employees, update_employee

# ---------- SIDOPPSETTNING ----------
def setup_page():
    """Konfigurerar Streamlit-sidan."""
    st.set_page_config(page_title="Chefsida", layout="wide")

setup_page()

# ---------- KONFIGURATION ----------
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
        "min_team_size"
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
        "min_team_size": 3               # Antal anställda per pass (min)
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

def can_work(emp, day, emp_state):
    """
    Kontrollerar om en anställd kan arbeta på given dag (max ett pass per dag),
    samt om medarbetaren inte redan uppnått sitt max antal pass eller max sammanhängande dagar.
    """
    state = emp_state[emp["id"]]
    if day in state["assigned_days"]:
        return False  # Redan schemalagd denna dag
    if state["worked_shifts"] >= state["max_shifts"]:
        return False  # Har nått max antal pass
    if state["last_worked_date"] is not None:
        delta = (day - state["last_worked_date"]).days
        if delta == 1 and state["consec_days"] >= emp["max_consec_days"]:
            return False
    return True

# ---------- BYGG FÄRGKODAD PIVOT I HTML ----------
def build_color_coded_pivot(schedule_df):
    """
    Skapar en HTML-pivot med färgkodade initialer.
    Index = Datum, Kolumner = Skift, Värde = "Personal (Initialer)"
    """
    pivot = schedule_df.pivot(index="Datum", columns="Skift", values="Personal (Initialer)")
    pivot = pivot.fillna("")
    pivot_html = pivot.to_html(escape=False)
    return pivot_html

# ---------- TILLDELA PASS FÖR EN DAG ----------
def assign_shifts_for_day(day, shifts, available_staff, emp_state, min_exp_req, min_team_size):
    """
    Tilldelar pass för en given dag.
    - Endast kombinationer med exakt "min_team_size" antal anställda testas.
    - En kombination godkänns om:
         • Totala erfarenhetspoäng ≥ min_exp_req
         • Om det finns kandidater med erfarenhet ≥ 4, så krävs att minst en sådan med i teamet
         • Alla medarbetare uppfyller sina övriga constraints
    - Bland de giltiga kombinationerna beräknas ett fairness-värde (baserat på nuvarande pass/planerade pass samt skiftpreferens).
    - Om en giltig kombination hittas väljs den slumpmässigt.
    Returnerar:
      assignments -> lista av (shift_info, team)
      emp_state   -> uppdaterad state
    """
    assignments = []

    shift_preference_map = {
        "Morgon": "Dagskift",
        "EM": "Kvällsskift",
        "Natt": "Nattjour"
    }

    for shift_info in shifts:
        valid_combos = []
        # Filtrera kandidater som kan jobba denna dag
        day_candidates = [emp for emp in available_staff if can_work(emp, day, emp_state)]
        experienced_available = any(emp["experience"] >= 4 for emp in day_candidates)

        # Endast kombinationer med exakt "min_team_size" anställda testas
        for combo in combinations(day_candidates, min_team_size):
            total_exp = sum(emp["experience"] for emp in combo)
            if total_exp < min_exp_req:
                continue
            if experienced_available and not any(emp["experience"] >= 4 for emp in combo):
                continue
            if not all(can_work(emp, day, emp_state) for emp in combo):
                continue

            # Beräkna fairness-värde: (worked_shifts / max_shifts) + eventuellt preferensstraff
            combo_fairness = 0
            pref_required = shift_preference_map.get(shift_info["shift"], None)
            for emp in combo:
                ratio = emp_state[emp["id"]]["worked_shifts"] / emp_state[emp["id"]]["max_shifts"]
                penalty = 0 if (pref_required and pref_required in emp["work_types"]) else 1
                combo_fairness += ratio + penalty
            combo_fairness /= len(combo)

            valid_combos.append((combo, combo_fairness))

        if valid_combos:
            min_fairness = min(valid_combos, key=lambda x: x[1])[1]
            best_options = [c for c in valid_combos if c[1] == min_fairness]
            chosen_combo, _ = random.choice(best_options)

            # Uppdatera emp_state för varje anställd i den valda kombinationen
            for emp in chosen_combo:
                state = emp_state[emp["id"]]
                state["worked_shifts"] += 1
                if state["last_worked_date"] is not None and (day - state["last_worked_date"]).days == 1:
                    state["consec_days"] += 1
                else:
                    state["consec_days"] = 1
                state["last_worked_date"] = day
                state["assigned_days"].add(day)

            assignments.append((shift_info, chosen_combo))
            for emp in chosen_combo:
                if emp in available_staff:
                    available_staff.remove(emp)
        else:
            assignments.append((shift_info, None))

    return assignments, emp_state

# ---------- SCHEMAGENERERING ----------
def generate_schedule(employees):
    st.info("Genererar schema...")

    # Hämta inställningar
    period_start = st.session_state["period_start"]
    period_length = st.session_state["period_length"]
    min_exp_req = st.session_state["min_experience_req"]
    min_team_size = st.session_state["min_team_size"]

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

    # Bygg datumlista
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

    # Konvertera employees -> dict
    staff = []
    for e in employees:
        try:
            exp_val = int(e[7])
        except:
            exp_val = 0
        base_max = round((e[3] / 100) * period_length)
        if base_max < 1:
            base_max = 1
        staff.append({
            "id": e[0],
            "name": e[2],
            "workload_percent": e[3],
            "work_types": e[4].split(",") if e[4] else [],
            "max_consec_days": e[5],
            "min_days_off": e[6],
            "experience": exp_val,
            "max_shifts": base_max
        })

    # Kontroll: minst en anställd med erf ≥ 4
    if not any(s["experience"] >= 4 for s in staff):
        st.error("Konflikt: Det måste finnas minst en anställd med erfarenhet 4 eller högre.")
        return

    # Initiera emp_state med sparat max_shifts
    emp_state = {}
    for s in staff:
        emp_state[s["id"]] = {
            "worked_shifts": 0,
            "last_worked_date": None,
            "consec_days": 0,
            "assigned_days": set(),
            "max_shifts": s["max_shifts"]
        }

    # Schemalägg dag för dag
    schedule = []
    failed_days = {}
    for day in dates:
        random.shuffle(staff)
        available_day = staff.copy()
        assignments, emp_state = assign_shifts_for_day(
            day, daily_shifts[day], available_day, emp_state, min_exp_req, min_team_size
        )
        for shift_info, combo in assignments:
            if combo is None:
                if day not in failed_days:
                    failed_days[day] = []
                failed_days[day].append(
                    f"{shift_info['shift']} (krav: erf≥{min_exp_req} och {min_team_size} anställda)"
                )
            schedule.append({"slot": shift_info, "assigned": combo})

    if failed_days:
        err_msgs = []
        for d, shifts_failed in failed_days.items():
            date_str = d.strftime("%Y-%m-%d")
            for sf in shifts_failed:
                err_msgs.append(f"{date_str}: {sf}")
        st.error("Följande pass kunde inte schemaläggas:\n" + "\n".join(err_msgs))

    palette = [
        "#FFD700", "#ADFF2F", "#FF69B4", "#87CEFA", "#FFA500",
        "#9370DB", "#40E0D0", "#F08080", "#98FB98", "#F5DEB3",
        "#C0C0C0", "#B0E0E6", "#FFB6C1", "#D8BFD8", "#BC8F8F",
        "#FFFFE0", "#B22222", "#DAA520", "#B8860B", "#556B2F"
    ]
    color_map = {}
    for i, s in enumerate(staff):
        color_map[s["id"]] = palette[i % len(palette)]

    schedule_rows = []
    for item in schedule:
        slot = item["slot"]
        combo = item["assigned"]
        if combo is None:
            initials_html = "–"
        else:
            parts = []
            for emp in combo:
                init = get_initials(emp["name"])
                color = color_map[emp["id"]]
                parts.append(
                    f'<span style="background-color:{color}; padding:2px 4px; border-radius:3px;">{init}</span>'
                )
            initials_html = " ".join(parts)
        schedule_rows.append({
            "Datum": slot["date"].strftime("%Y-%m-%d"),
            "Veckodag": slot["day"],
            "Skift": slot["shift"],
            "Tid": f"{slot['start']} - {slot['end']}",
            "Personal (Initialer)": initials_html
        })

    schedule_df = pd.DataFrame(schedule_rows)

    summary_rows = []
    for s in staff:
        summary_rows.append({
            "Namn": s["name"],
            "Pass": emp_state[s["id"]]["worked_shifts"]
        })
    summary_df = pd.DataFrame(summary_rows).sort_values("Namn")

    st.subheader("Schemalagd översikt (färgkodade initialer)")
    st.write(schedule_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    st.subheader("Översikt: Antal pass per anställd")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.subheader("Kalenderöversikt för kommande pass")
    pivot_html = build_color_coded_pivot(schedule_df)
    st.write(pivot_html, unsafe_allow_html=True)

    st.markdown("### Exportera schema till Excel")
    if st.button("Exportera schema till Excel"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            clean_schedule = schedule_df.copy()
            def strip_html(cell):
                if cell == "–":
                    return cell
                parts = []
                for segment in cell.split("</span>"):
                    if "<span" in segment:
                        txt = segment.split(">")[-1]
                        parts.append(txt)
                return " ".join(parts)
            clean_schedule["Personal (Initialer)"] = clean_schedule["Personal (Initialer)"].apply(strip_html)
            clean_schedule.to_excel(writer, index=False, sheet_name="Schema")
            summary_df.to_excel(writer, index=False, sheet_name="Sammanfattning")
        st.download_button(
            label="Ladda ner Excel",
            data=output.getvalue(),
            file_name="schema.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def show_chef_interface_wrapper():
    init_session()
    lang = LANGUAGES["sv"]
    st.title(f"👨💼 Chefssida - {st.session_state.hospital}")
    st.markdown("---")

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
    st.subheader("Schemainställningar")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        period_start = st.date_input("Startdatum", value=datetime(2025, 2, 16).date())
        st.session_state["period_start"] = period_start
    with col2:
        period_length = st.number_input("Antal dagar att schemalägga", min_value=7, max_value=90, value=60)
        st.session_state["period_length"] = period_length
    with col3:
        st.session_state["min_experience_req"] = st.slider(
            "Minsta totala erfarenhetspoäng per pass",
            min_value=1, max_value=50,
            value=st.session_state.get("min_experience_req", 10),
            step=1
        )
    with col4:
        st.session_state["min_team_size"] = st.slider(
            "Antal anställda per pass (min)",
            min_value=1, max_value=10,
            value=st.session_state.get("min_team_size", 3),
            step=1
        )

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
