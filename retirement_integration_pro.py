import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים "רמת פניקס" (תיקון פער גילאים ורטרו) ---
def calculate_phoenix_pro_coeff(gender, ret_age, guarantee, spouse_birth, emp_birth, survivor_pct, retro_months):
    # 1. מקדמי בסיס מנספח ו' ונספח ח' (גברים פרישה 67, נשים 62-65)
    if gender == 'גבר':
        # בסיס גיל 67 הוא 181.49. על כל שנת הקדמה המקדם עולה בכ-3.5 נקודות
        base = 181.49 + (67 - ret_age) * 3.45
    else:
        # בסיס אישה גיל 62 הוא 208.06.
        base = 208.06 + (62 - ret_age) * 3.7
    
    # 2. תוספת תקופת הבטחה (לפי לוחות הפניקס)
    guarantee_map = {0: 0, 60: 0.48, 120: 2.06, 180: 5.07, 240: 10.16}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    # 3. חישוב פער גילאים מדויק (הגורם המשפיע בנספח ח')
    # ככל שבן הזוג צעיר יותר, המקדם עולה ("פגיעה" בקצבה)
    age_diff = (emp_birth - spouse_birth).days / 365.25
    
    # הצלבת פער גילאים: תוספת של כ-0.14 למקדם על כל שנת פער (מעבר ל-3 שנים מובנות)
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.142
    elif age_diff < -3:
        coeff -= (abs(age_diff) - 3) * 0.11 # בן זוג מבוגר מקטין מקדם
        
    # 4. התאמת שיעור שאירים (ברירת מחדל 60%)
    # כל 10% תוספת לשאיר מוסיפה כ-1.55 נקודות למקדם
    coeff += (survivor_pct - 60) * 0.155
    
    # 5. חודשי רטרו (0-3 חודשים)
    # כל חודש רטרו "קונס" את המקדם בתוספת של כ-0.18%
    coeff *= (1 + (retro_months * 0.00185))
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה PRO", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")
    st.info("המנוע מסונכרן כעת עם נספחי המקדמים ופער הגילאים של הפניקס (יולי 2024)")

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1960, 5, 15))
        gender = st.selectbox("מין", ["גבר", "אישה"])
        ret_age = st.slider("גיל פרישה מתוכנן", 60.0, 75.0, 67.0, step=0.25)
        
        st.divider()
        st.header("👫 בן/ת זוג ושאירים")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1964, 1, 1))
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ הגדרות מסלול")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו (0-3)", [0, 1, 2, 3], index=0)

    # חישוב המקדם בזמן אמת - כל שינוי ב-Sidebar מפעיל את זה
    final_coeff = calculate_phoenix_pro_coeff(gender, ret_age, guarantee, spouse_birth, emp_birth, survivor_pct, retro_months)
    
    # --- תצוגת תוצאות ---
    st.subheader("📋 ריכוז נתוני פרישה")
    assets = st.number_input("צבירה פנסיונית כוללת (₪)", value=1000000.0, step=10000.0)
    pension = assets / final_coeff

    c1, c2, c3 = st.columns(3)
    c1.metric("מקדם משוקלל", f"{final_coeff:.2f}")
    c2.metric("קצבה ברוטו", f"₪{pension:,.0f}")
    c3.metric("קצבת שאיר", f"₪{pension * (survivor_pct/100):,.0f}")

    # הסבר דינמי על השפעת פער הגילאים
    age_diff_val = (emp_birth - spouse_birth).days / 365.25
    if age_diff_val > 3:
        st.warning(f"המקדם עלה בגלל שבן/ת הזוג צעיר/ה ב-{age_diff_val:.1f} שנים מהעמית.")
    elif age_diff_val < -3:
        st.success(f"המקדם קטן בגלל שבן/ת הזוג מבוגר/ת מהעמית.")

if __name__ == "__main__":
    main()
