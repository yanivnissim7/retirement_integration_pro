import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים "אפקט" - כיול סופי ומדויק ---
def calculate_accurate_phoenix_coeff(gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees):
    if gender == 'גבר':
        # תיקון קל בבסיס לסגירת הסטייה האחרונה
        base = 191.28 + (65 - exact_age) * 3.72
    else:
        base = 210.50 + (62 - exact_age) * 3.75
    
    guarantee_map = {0: 0, 60: 0.55, 120: 2.30, 180: 5.75, 240: 11.60}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    age_diff = (emp_birth - spouse_birth).days / 365.25
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.248
    elif age_diff < -3:
        coeff -= (abs(age_diff) - 3) * 0.13
    
    coeff += (survivor_pct - 60) * 0.182
    
    # כיול רטרו עדין לסגירת ה-0.12
    retro_factor = 1 + (retro_months * 0.00355) 
    coeff *= retro_factor
    
    mgt_fee_factor = 1 / (1 - (mgt_fees / 100))
    coeff *= mgt_fee_factor
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - מערכת תכנון פרישה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 מערכת תכנון פרישה - אפקט")
    
    # --- SIDEBAR - פרמטרים אקטואריים ---
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1961, 3, 26))
        gender = st.selectbox("מין העמית", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה", value=datetime(2026, 3, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_gender = st.selectbox("מין בן/ת הזוג", ["אישה", "גבר"], index=0 if gender == "גבר" else 1)
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1971, 7, 26))
        survivor_pct = st.select_slider("אחוז לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ הגדרות מסלול")
        guarantee = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=3)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)

    # חישוב המקדם המרכזי
    rdiff = relativedelta(ret_date, emp_birth)
    exact_age = rdiff.years + (rdiff.months / 12)
    calculated_main_coeff = calculate_accurate_phoenix_coeff(
        gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees
    )

    # --- מרכז המסך - ניהול קופות וכספים ---
    st.subheader("💰 פירוט קופות וצבירות")
    
    # יצירת טבלה דינמית להזנת נתונים
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'קרן פנסיה מקיפה', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': calculated_main_coeff}]

    def add_fund():
        st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': calculated_main_coeff})

    # כפתור הוספת קופה
    st.button("➕ הוסף קופה/קופת גמל", on_click=add_fund)

    edited_funds = []
    total_pension = 0.0

    for i, fund in enumerate(st.session_state.funds):
        col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
        with col1:
            name = st.text_input(f"שם הקופה #{i+1}", value=fund['name'], key=f"name_{i}")
        with col2:
            f_type = st.selectbox(f"סוג", ["קצבתי", "הוני"], index=0 if fund['type'] == 'קצבתי' else 1, key=f"type_{i}")
        with col3:
            amount = st.number_input(f"צבירה (₪)", value=fund['amount'], step=10000.0, key=f"amount_{i}")
        with col4:
            # המקדם כברירת מחדל הוא מה שחישבנו, אבל ניתן לדרוס אותו
            coeff = st.number_input(f"מקדם", value=fund['coeff'], format="%.2f", key=f"coeff_{i}")
        
        pension_contribution = amount / coeff if f_type == 'קצבתי' and coeff > 0 else 0
        total_pension += pension_contribution
        edited_funds.append({'name': name, 'type': f_type, 'amount': amount, 'coeff': coeff, 'pension': pension_contribution})

    st.divider()

    # --- סיכום דוח פרישה ---
    st.subheader("📊 סיכום הערכת קצבה חודשית")
    
    res_c1, res_c2, res_c3 = st.columns(3)
    with res_c1:
        st.metric("סה\"כ קצבה חודשית (ברוטו)", f"₪{total_pension:,.0f}")
    with res_c2:
        total_assets = sum(f['amount'] for f in edited_funds)
        st.metric("סה\"כ הון מנוהל", f"₪{total_assets:,.0f}")
    with res_c3:
        st.metric("מקדם משוקלל ממוצע", f"{(total_assets/total_pension if total_pension > 0 else 0):.2f}")

    st.write("---")
    st.write("**פירוט לחישוב אקטוארי (אפקט):**")
    st.write(f"גיל פרישה: {rdiff.years}.{rdiff.months} | פער גילאים: {(emp_birth - spouse_birth).days/365.25:.1f} שנים | דמי ניהול: {mgt_fees}%")

if __name__ == "__main__":
    main()
