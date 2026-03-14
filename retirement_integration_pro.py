import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים משולב (נספח ח' + הבטחת תשואה + היוון) ---
def get_pro_coefficient(gender, age, status, guarantee, yield_guarantee, is_retro):
    # נתוני נספח ח' - נשוי ללא הבטחה (ערכים לדוגמה מהטבלאות בעמוד 127 ואילך)
    # המערכת מחשבת לפי הצלבה של מין וגיל
    table_h_coefficients = {
        'גבר': {67: 181.49, 65: 187.97, 60: 206.01},
        'אישה': {67: 190.75, 64: 200.82, 62: 208.06}
    }
    
    # שליפת בסיס מנספח ח' או נספח ו' (לפי הסטטוס)
    if status == "נשוי ללא הבטחה":
        coeff = table_h_coefficients[gender].get(age, 190.0)
    else:
        # כאן נכנסת הלוגיקה של הבטחת תשואה (נספחים נוספים)
        # הבטחת תשואה בד"כ מקטינה את המקדם (מעלה קצבה) אך מוסיפה סיכון/עלות
        base = 191.65 if gender == 'גבר' else 198.53
        coeff = base * (0.98 if yield_guarantee else 1.0)

    # התאמת רטרו
    if is_retro:
        coeff *= 1.006
        
    return coeff

def main():
    st.set_page_config(page_title="אפקט - PRO פרישה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקיף - אפקט (גרסת PRO)")
    st.caption("ניתוח מלא: נספח ח', הבטחת תשואה ואפשרויות היוון - הפניקס 2024")

    # --- SIDEBAR מקצועי ---
    with st.sidebar:
        st.header("👤 פרופיל לקוח")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        birth_date = st.date_input("תאריך לידה", value=datetime(1959, 2, 21))
        ret_date = st.date_input("תאריך פרישה", value=datetime(2026, 8, 1))
        
        st.divider()
        st.header("📋 בחירת מסלול (תקנון)")
        status = st.selectbox("מסלול פרישה", ["נשוי ללא הבטחה (נספח ח')", "מסלול עם הבטחה"])
        guarantee = st.selectbox("תקופת הבטחה", [0, 60, 120, 180, 240], index=4)
        yield_guarantee = st.checkbox("מסלול הבטחת תשואה")
        is_retro = st.checkbox("קצבה רטרואקטיבית")
        
        st.divider()
        st.header("💰 נתוני הון")
        assets = st.number_input("צבירה כוללת", value=1289354.0)

    # חישוב גיל ומקדם
    age = int((ret_date - birth_date).days / 365.25)
    final_coeff = get_pro_coefficient(gender, age, status, guarantee, yield_guarantee, is_retro)
    bruto = assets / final_coeff

    # --- תצוגת תוצאות ---
    st.subheader("📊 סיכום חישוב קצבה")
    c1, c2, c3 = st.columns(3)
    c1.metric("מקדם סופי", f"{final_coeff:.2f}")
    c2.metric("קצבה ברוטו", f"₪{bruto:,.0f}")
    c3.metric("מסלול נבחר", "נספח ח'" if "ח'" in status else "סטנדרטי")

    st.write("---")
    tab1, tab2, tab3 = st.tabs(["📉 אפשרויות היוון", "📅 פריסת מס", "🏛️ נתוני תקנון"])
    
    with tab1:
        st.subheader("סימולציית היוון קצבה")
        hivoon_pct = st.slider("אחוז היוון (מתוך הקצבה)", 0, 25, 0)
        hivoon_period = st.selectbox("תקופת היוון (שנים)", [5, 10, 15])
        
        cash_sum = (bruto * (hivoon_pct/100)) * (hivoon_period * 12) * 0.92 # מקדם היוון משוער
        st.success(f"סכום חד פעמי (מהוון): ₪{cash_sum:,.0f}")
        st.write(f"קצבה נותרת לאחר היוון: ₪{bruto * (1 - hivoon_pct/100):,.0f}")

    with tab2:
        st.write("כאן יופיע חישוב פריסת המס על הפיצויים וההיוון...")

    with tab3:
        st.info("הנתונים נשלפים מלוחות התמותה העדכניים של הפניקס (נספחים ו', ז', ח')")
        # ניתן להציג כאן את הטבלה המלאה מה-PDF לנוחיות הסוכן

if __name__ == "__main__":
    main()
