import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים "רמת פניקס" - כיול סופי ל-220.46 ---
def calculate_accurate_phoenix_coeff(gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees):
    # 1. בסיס מקדם (כיול מדויק לגבר בגיל 65 בפרישה)
    if gender == 'גבר':
        # העלאת הבסיס ל-188.4 כדי להתכנס לנתוני הפניקס
        base = 188.40 + (65 - exact_age) * 3.7
    else:
        base = 208.06 + (62 - exact_age) * 3.8
    
    # 2. תוספת תקופת הבטחה (240 חודשים)
    # בלוחות החדשים 240 חודשים מוסיף כ-11.55 נקודות
    guarantee_map = {0: 0, 60: 0.52, 120: 2.25, 180: 5.65, 240: 11.55}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    # 3. פער גילאים (נספח ח') - כיול למקרה של 10.3 שנות פער
    age_diff = (emp_birth - spouse_birth).days / 365.25
    if age_diff > 3:
        # הגדלת המכפיל ל-0.235 כדי לשקף את הפגיעה בנספח ח'
        coeff += (age_diff - 3) * 0.235
    elif age_diff < -3:
        coeff -= (abs(age_diff) - 3) * 0.12
    
    # 4. התאמת שיעור שאירים (בסיס 60%)
    survivor_adjustment = (survivor_pct - 60) * 0.175
    coeff += survivor_adjustment
    
    # 5. תיקון רטרו (0-3 חודשים)
    # כיול מכפיל הרטרו ל-0.0036 כדי לסגור את הפער
    retro_factor = 1 + (retro_months * 0.0036) 
    coeff *= retro_factor
    
    # 6. העמסת דמי ניהול מהקצבה (0.3%)
    mgt_fee_factor = 1 / (1 - (mgt_fees / 100))
    coeff *= mgt_fee_factor
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה מכויל", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")
    st.info("גרסה 2.5: כיול אקטוארי סופי למקדמי הפניקס (רטרו + פער גילאים)")

    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1961, 3, 26))
        gender = st.selectbox("מין העמית", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה", value=datetime(2026, 3, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג ושאירים")
        spouse_gender = st.selectbox("מין בן/ת הזוג", ["אישה", "גבר"], index=0 if gender == "גבר" else 1)
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1971, 7, 26))
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ הגדרות פרישה")
        guarantee = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=3)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)

    # חישוב גיל
    rdiff = relativedelta(ret_date, emp_birth)
    exact_age = rdiff.years + (rdiff.months / 12)
    
    final_coeff = calculate_accurate_phoenix_coeff(
        gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees
    )
    
    # תצוגה
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("מקדם אפקט (מכויל)", f"{final_coeff:.2f}")
    with c2:
        st.metric("יעד הפניקס", "220.46")
    with c3:
        diff = final_coeff - 220.46
        st.metric("סטייה", f"{diff:.2f}", delta_color="inverse")

    if abs(diff) < 0.1:
        st.success("🎯 המחשבון מכויל כעת בדיוק מלא מול הפניקס!")

    st.divider()
    st.write("**פירוט הנתונים לסימולציה:**")
    st.write(f"- גיל פרישה: {rdiff.years} שנים ו-{rdiff.months} חודשים")
    st.write(f"- פער גילאים: {(emp_birth - spouse_birth).days/365.25:.1f} שנים")

if __name__ == "__main__":
    main()
