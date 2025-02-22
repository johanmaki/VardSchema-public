# pages/1_Chefsida.py
import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
from io import BytesIO
from itertools import combinations

from database import get_employees, update_employee

def setup_page():
    st.set_page_config(page_title="Chefsida", layout="wide")

setup_page()

LANGUAGES = {
    "sv": {
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

def init_session():
    required_keys = [
        "staff", "hospital", "min_experience_req", "period_start", "period_length",
        "morning_start", "morning_end", "em_start", "em_end", "night_start", "night_end",
        "min_team_size", "require_experienced", "prioritize_nattjour"
    ]
    defaults = {
        "staff": [],
        "hospital": "Karolinska",
        "min_experience_req": 1,       # Ändrat enligt testkrav
        "period_start": datetime(2025,2,16).date(),
        "period_length": 30,           # Kortare period för test
        "morning_start": "06:00",
        "morning_end": "14:00",
        "em_start": "14:00",
        "em_end": "22:00",
        "night_start": "22:00",
        "night_end": "06:00",
        "min_team_size": 1,            # Testa med 1 person per pass
        "require_experienced": False,  # För test, annars sätt True
        "prioritize_nattjour": False   # För test, annars sätt True
    }
    for key in required_keys:
        if key not in st.session_state:
            st.session_state[key] = defaults[key]

init_session()

def get_initials(name):
    parts = name.split()
    return "".join(p[0].upper() for p in parts if p)

def remove_employee(employee_id):
    try:
        from database import delete_employee
        delete_employee(employee_id)
        st.success("Anställd togs bort.")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Fel vid borttagning: {str(e)}")

def can_work(emp, day, emp_state):
    state = emp_state[emp["id"]]
    # Ta bort consec_days-kontroll
    if day in state["assigned_days"]:
        return False
    if state["worked_shifts"] >= state["max_shifts"]:
        return False
    return True

def parse_time(start_str, end_str):
    fmt = "%H:%M"
    t1 = datetime.strptime(start_str, fmt).time()
    t2 = datetime.strptime(end_str, fmt).time()
    if t1 == t2:
        t2 = datetime.strptime("06:00", fmt).time()
    return t1, t2

def build_color_coded_pivot(schedule_df):
    pivot = schedule_df.pivot(index="Datum", columns="Skift", values="Personal (Initialer)")
    pivot = pivot.fillna("")
    return pivot.to_html(escape=False)

def assign_shifts_for_day(day, shifts, available_staff, emp_state, min_exp_req, min_team_size, debug_logs):
    assignments = []
    require_experienced = st.session_state.get("require_experienced", True)
    prioritize_nattjour = st.session_state.get("prioritize_nattjour", False)
    
    for shift_info in shifts:
        shift_label = shift_info["shift"]
        day_candidates = [emp for emp in available_staff if can_work(emp, day, emp_state)]
        debug_logs.append(f"Datum: {day}, Skift: {shift_label}, Kandidater innan filtrering: {len(day_candidates)}")
        
        if shift_label == "Natt" and prioritize_nattjour:
            natt_candidates = [emp for emp in day_candidates if "Nattjour" in emp["work_types"]]
            if natt_candidates:
                day_candidates = natt_candidates
            debug_logs.append(f"Efter nattjour-filtrering: {len(day_candidates)} kandidater")
        
        day_candidates.sort(key=lambda e: emp_state[e["id"]]["worked_shifts"] / e["max_shifts"])
        debug_logs.append(f"Efter sortering: {', '.join([e['name'] for e in day_candidates])}")
        
        if len(day_candidates) < min_team_size:
            debug_logs.append(f"❌ Misslyckas: {len(day_candidates)} kandidater < min_team_size({min_team_size})")
            assignments.append((shift_info, None))
            continue
        
        chosen = day_candidates[:min_team_size]
        total_exp = sum(c["experience"] for c in chosen)
        debug_logs.append(f"Valda: {[c['name'] for c in chosen]}, total_exp={total_exp}")
        
        if total_exp < min_exp_req:
            debug_logs.append(f"❌ Misslyckas: total_exp({total_exp}) < min_exp_req({min_exp_req})")
            assignments.append((shift_info, None))
            continue
        
        if require_experienced and not any(c["experience"] >= 4 for c in chosen):
            debug_logs.append("❌ Misslyckas: require_experienced=True men ingen har erf≥4")
            assignments.append((shift_info, None))
            continue
        
        for emp in chosen:
            state = emp_state[emp["id"]]
            state["worked_shifts"] += 1
            state["last_worked_date"] = day
            state["assigned_days"].add(day)
            if emp in available_staff:
                available_staff.remove(emp)
        
        debug_logs.append(f"✅ Tilldelat: {[c['name'] for c in chosen]}")
        assignments.append((shift_info, chosen))
    
    return assignments, emp_state

def generate_schedule(employees):
    st.info("Genererar schema...")
    period_start = st.session_state["period_start"]
    period_length = st.session_state["period_length"]
    min_exp_req = st.session_state["min_experience_req"]
    min_team_size = st.session_state["min_team_size"]
    
    morning_s, morning_e = parse_time(st.session_state["morning_start"], st.session_state["morning_end"])
    em_s, em_e = parse_time(st.session_state["em_start"], st.session_state["em_end"])
    night_s, night_e = parse_time(st.session_state["night_start"], st.session_state["night_end"])
    
    shift_types = [
        {"shift": "Morgon", "start": morning_s.strftime("%H:%M"), "end": morning_e.strftime("%H:%M")},
        {"shift": "EM",     "start": em_s.strftime("%H:%M"),     "end": em_e.strftime("%H:%M")},
        {"shift": "Natt",   "start": night_s.strftime("%H:%M"),  "end": night_e.strftime("%H:%M")}
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
            "min_days_off": e[6],
            "experience": exp_val,
            "max_shifts": base_max
        })
    
    if st.session_state["require_experienced"]:
        if not any(s["experience"] >= 4 for s in staff):
            st.error("Konflikt: Kräver minst en anställd med erfarenhet 4 eller högre, men ingen finns.")
            return
    
    emp_state = {}
    for s in staff:
        emp_state[s["id"]] = {
            "worked_shifts": 0,
            "last_worked_date": None,
            "assigned_days": set(),
            "max_shifts": s["max_shifts"]
        }
    
    schedule = []
    failed_days = {}
    debug_logs = []
    
    for day in dates:
        random.shuffle(staff)
        available_day = staff.copy()
        assignments, emp_state = assign_shifts_for_day(
            day, daily_shifts[day], available_day, emp_state, min_exp_req, min_team_size, debug_logs
        )
        for shift_info, combo in assignments:
            if not combo:
                if day not in failed_days:
                    failed_days[day] = []
                failed_days[day].append(f"{shift_info['shift']} (krav: erf≥{min_exp_req}, minst {min_team_size} pers)")
            schedule.append({"slot": shift_info, "assigned": combo})
    
    if failed_days:
        err_msgs = []
        for d, shifts_failed in failed_days.items():
            ds = d.strftime("%Y-%m-%d")
            for sf in shifts_failed:
                err_msgs.append(f"{ds}: {sf}")
        st.error("Följande pass kunde inte schemaläggas:\n" + "\n".join(err_msgs))
    
    summary_rows = []
    for s in staff:
        summary_rows.append({"Namn": s["name"], "Pass": emp_state[s["id"]]["worked_shifts"]})
    summary_df = pd.DataFrame(summary_rows).sort_values("Namn")
    
    schedule_rows = []
    for item in schedule:
        slot = item["slot"]
        combo = item["assigned"]
        if combo:
            initials_html = " ".join(f'<span style="padding:2px 4px; border-radius:3px;">{get_initials(emp["name"])}</span>'
                                     for emp in combo)
        else:
            initials_html = "–"
        schedule_rows.append({
            "Datum": slot["date"].strftime("%Y-%m-%d"),
            "Veckodag": slot["day"],
            "Skift": slot["shift"],
            "Tid": f"{slot['start']} - {slot['end']}",
            "Personal (Initialer)": initials_html
        })
    
    schedule_df = pd.DataFrame(schedule_rows)
    
    st.subheader("Översikt: Antal pass per anställd")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    st.subheader("Kalenderöversikt för kommande pass")
    pivot_html = build_color_coded_pivot(schedule_df)
    st.write(pivot_html, unsafe_allow_html=True)
    
    with st.expander("Debug-info"):
        for line in debug_logs:
            st.write(line)
    
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
        st.download_button(label="Ladda ner Excel",
                           data=output.getvalue(),
                           file_name="schema.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def show_chef_interface_wrapper():
    init_session()
    st.title(f"👨💼 Chefssida - {st.session_state.hospital}")
    st.markdown("---")
    
    st.subheader("Hantera anställda")
    employees = get_employees(st.session_state.hospital)
    if employees:
        emp_options = {f"{e[2]} (ID: {e[0]})": e[0] for e in employees}
        to_delete = st.selectbox("Välj anställd att ta bort", options=list(emp_options.keys()))
        if st.button("Ta bort anställd"):
            delete_employee(emp_options[to_delete])
            st.experimental_rerun()
    else:
        st.info("Inga anställda finns att hantera.")
    
    st.markdown("---")
    st.header("👥 Personalhantering")
    if employees:
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
                    exp_index = max(0, int(current_exp)-1)
                    new_exp = st.selectbox("Erfarenhetsnivå",
                                           options=list(LANGUAGES["sv"]["experience_labels"].keys()),
                                           index=exp_index,
                                           format_func=lambda x: LANGUAGES["sv"]["experience_labels"][x])
                with col2:
                    work_types = st.multiselect("Arbetsformer",
                                                ["Nattjour", "Dagskift", "Kvällsskift", "Helg", "Administration"],
                                                default=emp_data[4].split(",") if emp_data[4] else [])
                    min_off = st.number_input("Minsta lediga dagar", min_value=1, max_value=3, value=emp_data[6])
                if st.form_submit_button("💾 Spara ändringar"):
                    update_data = {
                        "id": emp_id,
                        "workload": new_workload,
                        "work_types": work_types,
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
        st.session_state["period_start"] = st.date_input("Startdatum", value=datetime(2025,2,16).date())
    with col2:
        st.session_state["period_length"] = st.number_input("Antal dagar att schemalägga", min_value=7, max_value=90, value=30)
    with col3:
        st.session_state["min_experience_req"] = st.slider("Minsta totala erfarenhetspoäng per pass", 1, 50, 1, step=1)
    with col4:
        st.session_state["min_team_size"] = st.slider("Antal anställda per pass (min)", 1, 10, 1, step=1)
    
    st.checkbox("Kräv minst en med erfarenhet ≥ 4 per pass",
                value=st.session_state.get("require_experienced", False),
                key="require_experienced")
    st.checkbox("Prioritera endast 'Nattjour' på nattpass",
                value=st.session_state.get("prioritize_nattjour", False),
                key="prioritize_nattjour")
    
    st.markdown("### Skiftinställningar")
    colA, colB, colC = st.columns(3)
    with colA:
        morning_start = st.time_input("Morgonpass start", value=datetime.strptime("06:00", "%H:%M").time())
        st.session_state["morning_start"] = morning_start.strftime("%H:%M")
        morning_end = st.time_input("Morgonpass slut", value=datetime.strptime("14:00", "%H:%M").time())
        st.session_state["morning_end"] = morning_end.strftime("%H:%M")
    with colB:
        em_start = st.time_input("EM-pass start", value=datetime.strptime("14:00", "%H:%M").time())
        st.session_state["em_start"] = em_start.strftime("%H:%M")
        em_end = st.time_input("EM-pass slut", value=datetime.strptime("22:00", "%H:%M").time())
        st.session_state["em_end"] = em_end.strftime("%H:%M")
    with colC:
        night_start = st.time_input("Nattpass start", value=datetime.strptime("22:00", "%H:%M").time())
        st.session_state["night_start"] = night_start.strftime("%H:%M")
        night_end = st.time_input("Nattpass slut", value=datetime.strptime("06:00", "%H:%M").time())
        st.session_state["night_end"] = night_end.strftime("%H:%M")
    
    st.markdown("---")
    if st.button("🚀 Generera schema"):
        generate_schedule(get_employees(st.session_state["hospital"]))
    
    st.markdown("---")
    if st.button("🚪 Logga ut"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.markdown("<meta http-equiv='refresh' content='0; url=https://vardschema.streamlit.app/' />", unsafe_allow_html=True)
        st.stop()

show_chef_interface_wrapper()
