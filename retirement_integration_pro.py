import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי מנורה מבטחים (תקנון יוני 2025) ---
def calculate_menora_pension_coeff(gender, exact_age, guarantee_months, survivor_pct, age_diff, mgt_fees):
    # 1. טבלת עוגנים - מקדם בסיס (גבר, פרישה ב-67, 60% שאירים, 0 הבטחה, 0 דמי ניהול)
    # הערכים מבוססים על נספח ד' לתקנון מנורה (יוני 2025)
    anchors = {
        60: 172.50, 61: 176.20, 62: 180.10, 63: 184.20, 64: 188.50,
        65: 193.10, 66: 197.90, 67: 203.00, 68: 208.40, 69: 214.10, 70: 220.10
    }
    
    age_floor = int(exact_age)
    age_ceil = age_floor + 1
    
    if age_floor in anchors and age_ceil in anchors:
        base = anchors[age_floor] + (anchors[age_ceil] - anchors[age_floor]) * (exact_age - age_floor)
    else:
        base = 203.00 + (exact_age - 67) * 5.4

    # 2. תוספת הבטחת קצבאות (נספח ד') - כ-0.0483 לכל חודש
    # הערה: מעל גיל 67 מתבצע קיזוז אקטוארי אוטומטי
    effective_guarantee = guarantee_months
    if exact_age > 67 and guarantee_months > 0:
        effective_guarantee = max(0, guarantee_months - (exact_age - 67) * 12)
    
    guarantee_impact = (effective_guarantee / 240) * 11.60
    coeff = base + guarantee_impact
    
    # 3. נספח ח' - פער גילאים ושיעור שאירים
    # ככל שבת הזוג צעירה יותר (פער חיובי), המקדם עולה
    if age_diff > 3:
        # פקטור דינמי שגדל עם גיל הפורש
        dynamic_factor = 0.25 + (max(0, exact_age - 65) * 0.018)
        coeff += (age_diff - 3) * dynamic_factor
    
    # התאמה לאחוז שאיר (בסיס 60%)
    coeff += (survivor_pct - 60) * 0.19
    
    # 4. דמי ניהול מהקצבה (0.3% כברירת מחדל)
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return round(coeff, 2), int(effective_guarantee)

def main():
    st.set_page_config(page_title="מחשבון פרישה - אפקט & מנורה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - מנורה מבטחים")
    st.caption("מבוסס תקנון מנורה מבטחים מקיפה - מהדורת יוני 2025")

    # --- ריכוז פרמטרים לבחירה בסיידבר ---
    with st.sidebar:
        st.header("⚙️ פרמטרים לבחירה")
        
        # נתוני עמית
        emp_birth = st.date_input("תאריך לידה עמית", value=date(1965, 3, 26))
        gender = st.selectbox("מין", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה מבוקש", value=date(2032, 3, 26))
        
        st.divider()
        # נתוני בן/ת זוג ושאירים
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=date(1970, 1, 1))
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        # מסלול ודמי ניהול
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)
        
        # חישובים אקטואריים אוטומטיים
        rdiff = relativedelta(ret_date, emp_birth)
        exact_age = rdiff.years + (rdiff.months / 12)
        age_diff = (emp_birth - spouse_birth).days / 365.25
        
        current_coeff, eff_g = calculate_menora_pension_coeff(
            gender, exact_age, guarantee, survivor_pct, age_diff, mgt_fees
        )

        st.divider()
        st.subheader("📌 תוצאת חישוב")
        st.info(f"גיל פרישה: {rdiff.years} שנים ו-{rdiff.months} חודשים")
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; border:2px solid #ff4b4b; text-align:center;">
            <h1 style="color:#1f1f1f; margin:0;">{current_coeff:.2f}</h1>
            <p style='color:red; font-size:0.8em;'>{'הבטחה מקוזזת ל-'+str(eff_g) if eff_g < guarantee else ''}</p>
        </div>
        """, unsafe_allow_html=True)

    # --- טבלת כספים מרכזית ---
    st.subheader("💰 ריכוז צבירות לקצבה")
    
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים מקיפה', 'amount': 1000000.0}]

    col_add, col_clear = st.columns([1, 6])
    if col_add.button("➕ הוסף קופה"):
        st.session_state.funds.append({'name': '', 'amount': 0.0})
        st.rerun()
    if col_clear.button("🗑️ נקה הכל"):
        st.session_state.funds = [{'name': '', 'amount': 0.0}]
        st.rerun()

    total_pension = 0.0
    total_assets = 0.0

    for i, fund in enumerate(st.session_state.funds):
        with st.container():
            c1, c2, c3 = st.columns([3, 2, 1])
            fund['name'] = c1.text_input(f"שם הקופה/הקרן", value=fund['name'], key=f"n_{i}")
            fund['amount'] = c2.number_input(f"סכום צבירה (₪)", value=fund['amount'], key=f"a_{i}")
            # המקדם כאן מסונכרן תמיד לסיידבר אך ניתן לעריכה מקומית אם תרצה
            coeff_val = c3.number_input(f"מקדם", value=current_coeff, format="%.2f", key=f"c_{i}")
            
            pension_line = fund['amount'] / coeff_val if coeff_val > 0 else 0
            total_pension += pension_line
            total_assets += fund['amount']
        st.markdown("---")

    # סיכום סופי
    st.subheader("📊 סיכום פרישה צפוי")
    res1, res2, res3 = st.columns(3)
    res1.metric("סה\"כ קצבה חודשית (ברוטו)", f"₪{total_pension:,.0f}")
    res2.metric("סה\"כ צבירה מנוהלת", f"₪{total_assets:,.0f}")
    res3.metric("מקדם משוקלל", f"{ (total_assets / total_pension) if total_pension > 0 else 0:.2f}")

if __name__ == "__main__":
    main()
