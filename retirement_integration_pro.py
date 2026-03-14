import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים משולב רמת PRO (הפניקס 2024) ---
def calculate_advanced_coeff(gender, ret_age, guarantee, spouse_diff, survivor_pct, retro_months):
    # מקדמי בסיס מנספח ו' ונספח ח' (ערכים מייצגים מהטבלאות שהעלית)
    # גבר גיל 67 בסיס = 181.49, אישה גיל 62 בסיס = 208.06
    if gender == 'גבר':
        base = 181.49 + (67 - ret_age) * 3.5 # הערכה לינארית בין גילאים
    else:
        base = 208.06 + (62 - ret_age) * 3.8
    
    # תוספת תקופת הבטחה
    guarantee_map = {0: 0, 60: 0.5, 120: 2.1, 180: 5.1, 240: 10.2}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    # התאמת שיעור שאירים (סטנדרט 60%)
    # כל 10% מעל 60% מוסיפים כ-1.6 נקודות למקדם
    coeff += (survivor_pct - 60) * 0.16
    
    # "הפגיעה" בשל פער גילאים (נספח ח')
    # אם בן הזוג צעיר מהעמית (diff חיובי), המקדם עולה
    if spouse_diff > 0:
        coeff += (spouse_diff * 0.14)
        
    # התאמת חודשי רטרו (0-3)
    # תוספת של 0.2% למקדם לכל חודש רטרו
    coeff *= (1 + (retro_months * 0.002))
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה PRO", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")
    st.write("---")

    with st.sidebar:
        st.header("👤 פרטי העמית")
        birth_date = st.date_input("תאריך לידה", value=datetime(1960, 5, 15))
        gender = st.selectbox("מין", ["גבר", "אישה"])
        
        # חישוב גיל נוכחי
        today = datetime.now().date()
        age_now = relativedelta(today, birth_date)
        st.write(f"**גיל הלקוח היום:** {age_now.years} שנים ו-{age_now.months} חודשים")
        
        # בחירת גיל פרישה
        ret_age = st.slider("באיזה גיל הוא פורש?", 60, 75, 67)
        
        st.divider()
        st.header("👫 בן/ת זוג ושאירים")
        survivor_pct = st.selectbox("אחוז קצבה לשאיר", [30, 40, 50, 60, 75, 100], index=3)
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1964, 1, 1))
        
        # חישוב הפרש גילאים
        spouse_diff = (birth_date - spouse_birth).days / 365.25
        st.caption(f"הפרש גילאים: {spouse_diff:.1f} שנים")

        st.divider()
        st.header("⚙️ הגדרות מסלול")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.radio("חודשי רטרו", [0, 1, 2, 3], horizontal=True)

    # חישוב המקדם הסופי
    final_coeff = calculate_advanced_coeff(gender, ret_age, guarantee, spouse_diff, survivor_pct, retro_months)
    
    # הצגת תוצאות
    st.subheader("📋 ריכוז נתונים למבוטח")
    assets = st.number_input("יתרה צבורה (₪)", value=1000000.0, step=10000.0)
    pension = assets / final_coeff

    col1, col2, col3 = st.columns(3)
    col1.metric("מקדם משוקלל", f"{final_coeff:.2f}")
    col2.metric("קצבה חודשית (ברוטו)", f"₪{pension:,.0f}")
    col3.metric("קצבת שאיר", f"₪{pension * (survivor_pct/100):,.0f}")

    st.info(f"החישוב בוצע עבור פרישה בגיל {ret_age}. במידה והלקוח יפרוש בגיל {ret_age+1}, המקדם יקטן והקצבה תגדל.")

    # טאב להיוון וסל פטור
    st.write("---")
    t1, t2 = st.tabs(["📉 אפשרויות היוון", "📝 נוסחת הנסיגה"])
    with t1:
        st.write("כאן ניתן לחשב היוון של עד 25% מהקצבה ל-5 שנים.")
        h_pct = st.slider("אחוז היוון", 0, 25, 0)
        st.write(f"קצבה לאחר היוון: ₪{pension * (1 - h_pct/100):,.0f}")

if __name__ == "__main__":
    main()
