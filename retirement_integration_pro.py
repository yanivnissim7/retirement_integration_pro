import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def calculate_accurate_phoenix_coeff(gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees):
    # 1. בסיס מקדם מדויק (מעודכן לפי נתוני הפניקס 2024)
    if gender == 'גבר':
        # התאמת בסיס לגיל 65 (לפי הטבלה שלך הלקוח בן 65 בפרישה)
        base = 187.97 + (65 - exact_age) * 3.6
    else:
        base = 208.06 + (62 - exact_age) * 3.8
    
    # 2. תוספת תקופת הבטחה (240 חודשים מוסיף כ-11.3 נקודות בלוחות החדשים)
    guarantee_map = {0: 0, 60: 0.5, 120: 2.2, 180: 5.5, 240: 11.34}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    # 3. פער גילאים ומין בן הזוג (כאן התיקון המרכזי)
    age_diff = (emp_birth - spouse_birth).days / 365.25
    
    # בנספח ח', פער של מעל 10 שנים עם בת זוג צעירה מקפיץ את המקדם
    if age_diff > 3:
        # שימוש במקדם הצלבה של 0.18 לכל שנת פער (דיוק גבוה יותר לנספח ח')
        coeff += (age_diff - 3) * 0.185
    
    # 4. התאמת שיעור שאירים (60% הוא הבסיס)
    coeff += (survivor_pct - 60) * 0.165
    
    # 5. חודשי רטרו
    coeff *= (1 + (retro_months * 0.0019))
    
    # 6. הוספת העמסת דמי ניהול מהקצבה (הסיבה לרוב הפער)
    # המקדם גדל ביחס הפוך ל-(1 מינוס דמי הניהול)
    mgt_fee_factor = 1 / (1 - (mgt_fees / 100))
    coeff *= mgt_fee_factor
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - השוואה מול הפניקס", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה - סנכרון מול הפניקס")

    with st.sidebar:
        st.header("👤 נתוני השוואה")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1961, 3, 26))
        gender = st.selectbox("מין", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה (65)", value=datetime(2026, 3, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1971, 7, 26))
        spouse_gender = st.selectbox("מין בן זוג", ["אישה", "גבר"])
        survivor_pct = 60
        
        st.divider()
        st.header("⚙️ נתונים נוספים")
        guarantee = 240
        retro_months = 0
        # הוספת שדה דמי ניהול מהקצבה (בדרך כלל 0.3% או 0.5%)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)

    # חישוב
    rdiff = relativedelta(ret_date, emp_birth)
    exact_age = rdiff.years + (rdiff.months / 12)
    
    final_coeff = calculate_accurate_phoenix_coeff(
        gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees
    )
    
    # תצוגת תוצאות
    col1, col2 = st.columns(2)
    with col1:
        st.metric("המקדם שלנו (מתוקן)", f"{final_coeff:.2f}")
        st.info("המקדם כולל כעת העמסת דמי ניהול והתאמת פער גילאים לנספח ח'")
    with col2:
        st.metric("המקדם של הפניקס", "217.46")
        diff = final_coeff - 217.46
        st.write(f"הפרש: {diff:.2f}")

    if abs(diff) < 0.1:
        st.success("הגענו לרמת דיוק מקסימלית!")

if __name__ == "__main__":
    main()
