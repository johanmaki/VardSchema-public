# pages/1_Chefsida.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from database import get_employees, update_employee
from datetime import datetime

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

# ========== INITIERING AV SESSION ==========
# Se till att nödvändiga nycklar finns i sessionen. Ingen rollkontroll görs här.
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
                        st.stop()  # Stop execution instead of rerunning
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

# ========== SCHEMAGENERERING ==========
def generate_schedule(employees: list[tuple]) -> None:
    """
    Generera schema baserat på anställdas data.
    
    Args:
        employees (list[tuple]): En lista med anställdas data.
    
    Raises:
        ValueError: Om ingen anställd har tillräcklig erfarenhet.
    """
    try:
        # Konvertera anställdas data till en lista med dictionaries
        staff = [{
            "name": e[2],
            "experience": int(e[7]) if isinstance(e[7], (int, str)) and str(e[7]).isdigit() else 0,
            "work_types": e[4].split(",") if e[4] else [],
            "max_consec_days": e[5],
            "min_days_off": e[6]
        } for e in employees]

        # Kontroll: minst en anställd måste ha erfarenhet >= 4
        if not any(emp["experience"] >= 4 for emp in staff):
            st.error("Konflikt: Det måste finnas minst en anställd med erfarenhet 4 eller högre för att utse en ledningsansvarig.")
            return

        days = LANGUAGES["sv"]["days"]
        schedule_data = []
        eligible = [emp for emp in staff if emp["experience"] >= 4]
        # Skapa schema för varje dag
        for i, day in enumerate(days):
            leader = eligible[i % len(eligible)] if eligible else None
            leader_name = leader['name'].replace(" ★", "") if leader else "Ingen ledare"
            all_staff = [emp["name"] for emp in staff]
            schedule_data.append({
                "Dag": day,
                "Ledningsansvarig": leader_name,
                "Personal": ", ".join(all_staff),
                "Poäng": len(all_staff)  # Dummy-poäng baserat på antalet anställda
            })
        schedule_df = pd.DataFrame(schedule_data)
        
        # Visa schema med bakgrundsgradient på den numeriska kolumnen "Poäng"
        st.dataframe(
            schedule_df.style.background_gradient(subset=["Poäng"], cmap="YlGnBu"),
            hide_index=True,
            use_container_width=True
        )

        # Visuell representation med stapeldiagram
        fig, ax = plt.subplots()
        # Använd numeriska x-värden och sätt sedan x-tick etiketter
        x = range(len(schedule_df))
        ax.bar(
            x,
            schedule_df["Poäng"],
            color=THEME_COLORS["dark" if st.session_state.dark_mode else "light"]["primary"]
        )
        ax.set_xticks(x)
        ax.set_xticklabels(schedule_df["Dag"])
        ax.set_ylabel("Poäng")
        ax.set_title("Antal anställda per dag")
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Kunde inte generera schema: {str(e)}")

# Anropa chefsidans gränssnitt så att sidan renderas
show_chef_interface()
