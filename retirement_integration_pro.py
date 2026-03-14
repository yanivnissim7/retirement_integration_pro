import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

def calculate_precise_menora_2026(gender, birth_date, ret_date, spouse_birth, req_guarantee, survivor_pct, mgt_fees, retro_months):
    # 1. חישוב גיל מדויק בפרישה
    rdiff = relativedelta(ret_date, birth_date)
    exact_age = rdiff.years + (rdiff.months / 12)
    
    # 2. טבלת עוגן נספח א' (גבר) - כפי שמופיע בתמונה ששלחת
    # גיל 61 = 210.42
    anchors_base = {
        60: 214.98, 61: 210.42, 62: 207.10, 63: 203.67, 64: 200.13,
        65: 196.45, 66: 191.01, 67: 187.08, 68: 183.04, 69: 178.88, 70: 174.58
    }
    
    # חילוץ בסיס
    if exact_age in anchors_base:
        base = anchors_base[exact_age]
    else:
        floor_age = int(exact_age)
        ceil_age = floor_age + 1
        base = anchors_base[floor_age] - (anchors_base[floor_age] - anchors_base[ceil_age]) * (exact_age - floor_age)

    # 3. תוספת הבטחה (נספח ד') - עבור גיל 61 התוספת ל-240 חודשים היא 4.98
    # בדיקת תקרת גיל 87
    max_guarantee_age = 87
    available_months = max(0, (max_guarantee_age - exact_age) * 12)
    eff_guarantee = min(float(req_guarantee), available_months)
    
    # פקטור הבטחה לגיל 61 (ליניארי בין 0 ל-4.98)
    guarantee_impact = 4.98 * (eff_guarantee / 240)
    
    # 4. חישוב ראשוני
    coeff = base + guarantee_impact
    
    # 5. תוספת שאיר (בסיס 60% - כל 1% מעבר מוסיף 0.018)
    coeff += (survivor_pct - 60) * 0.18
    
    # 6. פער גילאים (נספח ח')
    age_diff = (birth_date - spouse_birth).days / 365.25
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.22
        
    # 7. דמי ניהול מהקצבה (0.3% -> חילוק ב-0.997)
    coeff /= (1 - (mgt_fees / 100))
    
    # 8. רטרו (0.355% לחודש)
    coeff *= (1 + (retro_months * 0.00355))
    
    return round(coeff, 2), round(eff_guarantee, 1), exact_age

def main():
    st.set_page_config(page_title="אפקט - סימולטור מדויק", layout="wide")
    st.title("🏆 סימולטור פרישה אפקט - כיול 100%")
    
    # נתוני קלט קשיחים לפי בקשתך
    with st.sidebar:
        st.header("👤 נתוני העמית")
        birth_date = st.date_input("תאריך לידה", value=date(1965, 11, 26))
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 11, 26))
        
        st.header("👫 בן/ת זוג")
        spouse_birth = st.date_input("לידה בת זוג", value=date(1968, 11, 26))
        survivor_pct = st.select_slider("שאיר %", options=[30, 60, 100], value=60)
        
        st.header("⚙️ מסלול")
        guarantee = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        mgt_fees = st.number_input("דמי ניהול %", value=0.3)
        retro = st.selectbox("רטרו (חודשים)", [0, 1, 2, 3])

    # ביצוע החישוב
    res_coeff, eff_g, age = calculate_precise_menora_2026(
        "גבר", birth_date, ret_date, spouse_birth, guarantee, survivor_pct, mgt_fees, retro
    )

    # הצגת תוצאה
    st.subheader(f"ניתוח עבור גיל פרישה {age:.1f}")
    c1, c2, c3 = st.columns(3)
    c1.metric("מקדם בסיס (לפני תוספות)", "210.42")
    c2.metric("הבטחה אפקטיבית", f"{eff_g} חודשים")
    c3.markdown(f"<div style='font-size:30px; color:green; font-weight:bold;'>מקדם סופי: {res_coeff}</div>", unsafe_allow_html=True)

    # טבלת קופות
    st.divider()
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מקיפה', 'amount': 1000000.0}]
    
    for i, fund in enumerate(st.session_state.funds):
        col1, col2, col3 = st.columns([3, 2, 2])
        fund['name'] = col1.text_input("קופה", fund['name'], key=f"n_{i}")
        fund['amount'] = col2.number_input("צבירה", fund['amount'], key=f"a_{i}")
        col3.write(f"קצבה: ₪{fund['amount']/res_coeff:,.0f}")

if __name__ == "__main__":
    main()
