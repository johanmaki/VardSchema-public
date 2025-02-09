# pages/1_Chefsida.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import random
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
    required_keys = ["staff", "dark_mode", "language"]
    for key in required_keys:
        if key not in st.session_state:
            st.session_state[key] = [] if key == "staff" else False if key == "dark_mode" else "sv"

# ========== CHEFSGRÄNSSNITT ==========
def show_chef_interface():
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
        return
    
    # Konvertera employee-listan till en DataFrame
    # Förväntade index: 0: ID, 2: Namn, 3: Arbetsbelastning, 4: Arbetsformer (sträng), 5: Max dagar, 6: Min lediga, 7: Erfarenhet
    df = pd.DataFrame(employees, columns=["ID", "Col1", "Namn", "Arbetsbelastning (%)", "Arbetsformer", "Max sammanhängande dagar", "Minsta lediga dagar", "Erfarenhet"])
    if "Col1" in df.columns:
        df.drop(columns=["Col1"], inplace=True)
    df["Erfarenhet"] = df["Erfarenhet"].astype(int)
    
    st.write("Redigera anställdas preferenser nedan:")
    edited_df = st.experimental_data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="employee_editor"
    )
    
    if st.button("💾 Spara ändringar"):
        for _, row in edited_df.iterrows():
            update_data = {
                "id": int(row["ID"]),
                "workload": int(row["Arbetsbelastning (%)"]),
                "work_types": row["Arbetsformer"],
                "max_consec_days": int(row["Max sammanhängande dagar"]),
                "min_days_off": int(row["Minsta lediga dagar"]),
                "experience": int(row["Erfarenhet"])
            }
            update_employee(update_data)
        st.success("Ändringar sparade!")
        st.experimental_rerun()
    
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
        # Hämta de eventuellt uppdaterade preferenserna från databasen
        updated_employees = get_employees(st.session_state.hospital)
        generate_schedule(updated_employees)

# ========== SCHEMAGENERERING ==========
def generate_schedule(employees):
    try:
        # Konvertera anställdas data till en lista med dicts
        staff = [{
            "name": e[2],
            "experience": int(e[7]),
            "work_types": e[4].split(",") if e[4] else [],
            "max_consec_days": int(e[5]),
            "min_days_off": int(e[6])
        } for e in employees]
        
        # Kontroll: minst en anställd måste ha erfarenhet >= 4
        if not any(emp["experience"] >= 4 for emp in staff):
            st.error("Konflikt: Det måste finnas minst en anställd med erfarenhet 4 eller högre för att utse en ledningsansvarig.")
            return
        
        # Dummy-schemagenerering: för varje dag i veckan, välj en ledare bland de med erfarenhet >= 4
        days = LANGUAGES["sv"]["days"]
        schedule_data = []
        eligible = [emp for emp in staff if emp["experience"] >= 4]
        # För att jämnt fördela ledarskapet kan vi rotera listan
        random.shuffle(eligible)
        for i, day in enumerate(days):
            if eligible:
                leader = eligible[i % len(eligible)]
                leader_name = f"{leader['name']} ★"
            else:
                leader_name = "Ingen ledare"
            # I en riktig implementation skulle personalen för varje pass väljas utifrån fler kriterier
            all_staff = ", ".join([emp["name"] for emp in staff])
            schedule_data.append({
                "Dag": day,
                "Ledningsansvarig": leader_name,
                "Personal": all_staff
            })
        
        schedule_df = pd.DataFrame(schedule_data)
        st.dataframe(
            schedule_df.style.background_gradient(subset=["Ledningsansvarig"], cmap="YlGnBu"),
            hide_index=True,
            use_container_width=True
        )
        
        # Visuell representation (exempel med dummy-poäng)
        fig, ax = plt.subplots()
        schedule_df["Poäng"] = schedule_df["Personal"].apply(lambda x: len(x))  # dummy-poäng
        ax.bar(schedule_df["Dag"], schedule_df["Poäng"], color=THEME_COLORS["dark" if st.session_state.dark_mode else "light"]["primary"])
        st.pyplot(fig)
        
    except Exception as e:
        st.error(f"Kunde inte generera schema: {str(e)}")

# ========== SIDHANTERING ==========
def main():
    if "user_type" not in st.session_state or st.session_state.user_type != "chef":
        st.error("Åtkomst nekad")
        st.stop()
    
    st.set_page_config(page_title="Chefsida", layout="wide")
    show_chef_interface()
    
    st.markdown("---")
    if st.button("🔒 Logga ut"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

if __name__ == "__main__":
    main()
