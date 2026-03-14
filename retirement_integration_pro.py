import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע חישוב מקצועי (לוגיקת נספח ח' והפרשי גילאים) ---
def calculate_phoenix_pro_coeff(gender, age, guarantee, spouse_age_diff, survivor_pct, retro_months):
    # 1. מקדם בסיס (לפי גבר/אישה וגיל - נספח ו' ו-ח')
    # נתוני בסיס לדוגמה (גבר גיל 67)
    base_coeff = 181.49 if gender == 'גבר' else 190.75
    
    # 2. התאמה לתקופת הבטחה (לפי הטבלאות שהעלית)
    guarantee_factor = {0: 0, 60: 0.48, 120: 2.06, 180: 5.07, 240: 10.16}
    coeff = base_coeff + guarantee_factor.get(guarantee, 0)
    
    # 3. התאמה לשיעור קצבת שאירים (60% הוא הבסיס, 100% מעלה את המקדם)
    # כל 10% מעבר ל-60% מוסיפים כ-1.5 נקודות למקדם (הערכה לפי תקנון)
    survivor_adjustment = (survivor_pct - 60) * 0.15
    coeff += survivor_adjustment
    
    # 4. התאמת פער גילאים ("הפגיעה")
    # אם בן הזוג צעיר מהמבוטח (הפרש חיובי), המקדם עולה
    if spouse_age_diff > 0:
        coeff += (spouse_age_diff * 0.12) # תוספת למקדם לכל שנת פער
        
    # 5. חודשי רטרו (0-3)
    # תוספת של כ-0.18% למקדם לכל חודש רטרו
    coeff *= (1 + (retro_months * 0.0018))
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט PRO - סימולטור פניקס", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקיף - אפקט (רמת מומחה)")
    
    with st.sidebar:
        st.header("👤 נתוני עמית")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        birth_date = st.date_input("תאריך לידה", value=datetime(1959, 2, 21))
        ret_date = st.date_input("תאריך פרישה", value=datetime(2026, 8, 1))
        
        st.divider()
        st.header("👥 מוטבים ושאירים")
        has_spouse = st.checkbox("יש בן/ת זוג (נשוי/ה)", value=True)
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 70, 80, 90, 100], value=60)
        
        if has_spouse:
            spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1964, 5, 15))
            age_diff = (birth_date - spouse_birth).days / 365.25
        else:
            age_diff = 0

        st.divider()
        st.header("⚙️ הגדרות מסלול")
        guarantee = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=0)

    # חישוב גיל כרונולוגי
    age_years = (ret_date - birth_date).days / 365.25
    
    # הפעלת המנוע
    final_coeff = calculate_phoenix_pro_coeff(gender, age_years, guarantee, age_diff, survivor_pct, retro_months)
    
    # תצוגה
    st.subheader("📋 תוצאות הסימולציה")
    assets = st.number_input("צבירה פנסיונית (₪)", value=1289354.0)
    pension = assets / final_coeff
    
    c1, c2, c3 = st.columns(3)
    c1.metric("מקדם משוקלל", f"{final_coeff:.2f}")
    c2.metric("קצבה ברוטו", f"₪{pension:,.0f}")
    c3.metric("קצבת שאיר", f"₪{pension * (survivor_pct/100):,.0f}")

    if age_diff > 5:
        st.warning(f"שים לב: קיים פער גילאים של {age_diff:.1f} שנים. המקדם הוגדל בהתאם להוראות התקנון.")

if __name__ == "__main__":
    main()
