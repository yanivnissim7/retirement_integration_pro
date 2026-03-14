import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי מעודכן לפי הטבלה הספציפית שהעלית ---
def calculate_menora_pension_coeff(gender, exact_age, guarantee_months, survivor_pct, age_diff, retro_months, mgt_fees):
    # טבלת עוגנים מעודכנת לפי התמונה (נספח א' - גבר)
    # גיל 60 = 214.98, גיל 61 = 210.42 וכו'
    anchors = {
        60: 214.98, 61: 210.42, 62: 207.10, 63: 203.67, 64: 200.13,
        65: 196.45, 66: 191.01, 67: 187.08, 68: 183.04, 69: 178.88, 70: 174.58
    }
    
    age_floor = int(exact_age)
    age_ceil = age_floor + 1
    
    # חישוב בסיס לפי גיל מדויק
    if age_floor in anchors and age_ceil in anchors:
        base = anchors[age_floor] - (anchors[age_floor] - anchors[age_ceil]) * (exact_age - age_floor)
    elif age_floor in anchors:
        base = anchors[age_floor]
    else:
        # אקסטרפולציה למקרה של גיל מבוגר מאוד
        base = 174.58 - (exact_age - 70) * 4.2

    # תוספת הבטחה (בטבלה ששלחת המקדמים הם ל-0 הבטחה)
    # תוספת מקובלת ל-240 חודשים היא באזור ה-4.5 עד 5 נקודות למקדם
    guarantee_impact = (guarantee_months / 240) * 4.85
    coeff = base + guarantee_impact
    
    # נספח ח' - פער גילאים (אם בת הזוג צעירה ב-3 שנים ומעלה)
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.22
    
    # התאמה לאחוז שאיר (הטבלה היא ל-60%)
    coeff += (survivor_pct - 60) * 0.18
    
    # רטרו
    coeff *= (1 + (retro_months * 0.00355))
    
    # דמי ניהול (מגדילים את המקדם כי הם מקטינים את הקצבה נטו)
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return round(coeff, 2)

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה - אפקט (מסונכרן לטבלה)")

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=date(1965, 3, 26))
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 3, 26)) # גיל 61
        
        st.divider()
        st.header("👫 בת זוג")
        spouse_birth = st.date_input("תאריך לידה בת זוג", value=date(1968, 1, 1))
        survivor_pct = st.select_slider("אחוז לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ מסלול")
        guarantee = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=0)
        mgt_fees = st.number_input("דמי ניהול (%)", value=0.3, step=0.1)

        # חישובים
        rdiff = relativedelta(ret_date, emp_birth)
        exact_age_ret = rdiff.years + (rdiff.months / 12)
        today_diff = relativedelta(date.today(), emp_birth)
        age_diff_val = (emp_birth - spouse_birth).days / 365.25
        
        target_coeff = calculate_menora_pension_coeff(
            "גבר", exact_age_ret, guarantee, survivor_pct, age_diff_val, retro_months, mgt_fees
        )

        st.divider()
        st.subheader("📊 נתונים מחושבים")
        st.write(f"**גיל כיום:** {today_diff.years}.{today_diff.months}")
        st.write(f"**גיל בפרישה:** {rdiff.years}.{rdiff.months}")
        st.success(f"מקדם מטרה: {target_coeff:.2f}")

    # --- טבלה ---
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מקיפה', 'type': 'קצבתי', 'amount': 1000000.0}]

    for i, fund in enumerate(st.session_state.funds):
        col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
        fund['name'] = col1.text_input("קופה", fund['name'], key=f"n_{i}")
        fund['type'] = col2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
        fund['amount'] = col3.number_input("צבירה", fund['amount'], key=f"a_{i}")
        if fund['type'] == "קצבתי":
            val = col4.number_input("מקדם", value=target_coeff, key=f"c_{i}")
        else:
            col4.write("הוני")

    # סיכום
    pension = sum([f['amount']/target_coeff for f in st.session_state.funds if f['type']=="קצבתי"])
    st.metric("קצבה צפויה", f"₪{pension:,.0f}")

if __name__ == "__main__":
    main()
