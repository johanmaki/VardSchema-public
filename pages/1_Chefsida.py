# pages/1_Chefsida.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from database import get_employees, update_employee
from datetime import datetime

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

# ========== INITIERING ==========
def init_session():
    required_keys = ["staff", "dark_mode", "language", "user_type", "hospital"]
    for key in required_keys:
        if key not in st.session_state:
            if key == "staff":
                st.session_state[key] = []
            elif key == "dark_mode":
                st.session_state[key] = False
            elif key == "language":
                st.session_state[key] = "sv"
            elif key == "user_type":
                st.session_state[key] = None
            elif key == "hospital":
                st.session_state[key] = "Karolinska"

# ========== CHEFSGRÄNSSNITT ==========
def show_chef_interface():
    init_session()
    lang = LANGUAGES["sv"]

    # Header
    st.title(f"👨‍💼 Chefssida - {st.session_state.hospital}")
    st.markdown("---")

    # Hämta personal från databasen
    employees = get_employees(st.session_state.hospital)

    # Personalredigering
    st.header("👥 Personalhantering")

    if not employees:
        st.warning("Inga anställda registrerade ännu.")
        return

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
                update_employee(update_data)
                st.success("Ändringar sparade!")
                st.rerun()

    # Schemagenerering
    st.markdown("---")
    st.header("🗕️ Schemagenerering")

    if st.button("🚀 Generera schema"):
        generate_schedule(employees)

# ========== SCHEMAGENERERING ==========
def generate_schedule(employees):
    try:
        staff = [{
            "name": e[2],
            "experience": e[7],
            "work_types": e[4].split(","),
            "max_consec_days": e[5],
            "min_days_off": e[6]
        } for e in employees]

        schedule_df = pd.DataFrame({
            "Dag": LANGUAGES["sv"]["days"],
            "Personal": ["Sven, Anna", "Erik, Lisa", "Maria, Peter", "Oscar, Lena", "Karin, Lars", "Mikael, Sofia", "Ingrid, Björn"],
            "Poäng": [25, 28, 23, 26, 24, 27, 22]
        })

        st.dataframe(
            schedule_df.style.background_gradient(subset=["Poäng"], cmap="Blues"),
            hide_index=True,
            use_container_width=True
        )

        fig, ax = plt.subplots()
        ax.bar(schedule_df["Dag"], schedule_df["Poäng"], color=THEME_COLORS["dark" if st.session_state.dark_mode else "light"]["primary"])
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Kunde inte generera schema: {str(e)}")

# ========== SIDHANTERING ==========
def main():
    init_session()
    if st.button("Logga in som chef"):
        st.session_state.user_type = "chef"

    if st.session_state.user_type == "chef":
        st.set_page_config(page_title="Chefsida", layout="wide")
        show_chef_interface()

        st.markdown("---")
        if st.button("🔒 Logga ut"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    else:
        st.error("Åtkomst nekad. Klicka på 'Logga in som chef' för att fortsätta.")

if __name__ == "__main__":
    main()
