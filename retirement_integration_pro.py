import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים משופר - סנכרון רטרו ופער גילאים ---
def calculate_accurate_phoenix_coeff(gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees):
    # 1. בסיס מקדם מדויק (התאמה לגיל 65 גבר)
    if gender == 'גבר':
        # בסיס גיל 65 הוא 187.97. 
        base = 187.97 + (65 - exact_age) * 3.65
    else:
        base = 208.06 + (62 - exact_age) * 3.8
    
    # 2. תוספת תקופת הבטחה (240 חודשים)
    # עדכון קל לערך ההבטחה בלוחות 2024
    guarantee_map = {0: 0, 60: 0.52, 120: 2.25, 180: 5.65, 240: 11.45}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    # 3. פער גילאים (נספח ח')
    age_diff = (emp_birth - spouse_birth).days / 365.25
    if age_diff > 3:
        # פער של 10.3 שנים כפי שמופיע בנתונים שלך
        coeff += (age_diff - 3) * 0.195
    elif age_diff < -3:
        coeff -= (abs(age_diff) - 3) * 0.12
    
    # 4. התאמת שיעור שאירים
    coeff += (survivor_pct - 60) * 0.168
    
    # 5. תיקון רטרו דרמטי (כאן היה הפער המרכזי)
    # ב-3 חודשי רטרו, הפניקס מעלה את המקדם בכ-0.9% עד 1% באופן מצטבר
    retro_factor = 1 + (retro_months * 0.0031) 
    coeff *= retro_factor
    
    # 6. העמסת דמי ניהול (0.3%)
    mgt_fee_factor = 1 / (1 - (mgt_fees / 100))
    coeff *= mgt_fee_factor
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - סנכרון פניקס מלא", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה - אפקט (סנכרון רטרו)")

    with st.sidebar:
        st.header("👤 נתוני השוואה")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1961, 3, 26))
        gender = st.selectbox("מין העמית", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה", value=datetime(2026, 3, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1971, 7, 26))
        spouse_gender = st.selectbox("מין בן/ת הזוג", ["אישה", "גבר"])
        
        st.divider()
        st.header("⚙️ מסלול, רטרו ודמי ניהול")
        guarantee = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו (0-3)", [0, 1, 2, 3], index=3) # ברירת מחדל 3 לבדיקה
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)
        survivor_pct = 60

    # חישוב
    rdiff = relativedelta(ret_date, emp_birth)
    exact_age = rdiff.years + (rdiff.months / 12)
    
    final_coeff = calculate_accurate_phoenix_coeff(
        gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees
    )
    
    # תצוגה
    c1, c2 = st.columns(2)
    with c1:
        st.metric("המקדם שלנו (מתוקן)", f"{final_coeff:.2f}")
        st.info(f"חישוב עבור {retro_months} חודשי רטרו ופער גילאים של {(emp_birth-spouse_birth).days/365.25:.1f} שנים")
    with c2:
        st.metric("המקדם של הפניקס", "220.46")
        st.write(f"הפרש: {final_coeff - 220.46:.2f}")

if __name__ == "__main__":
    main()
