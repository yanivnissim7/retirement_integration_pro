import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים משולב "רמת פניקס" (דיוק חודשים ופער גילאים) ---
def calculate_phoenix_pro_coeff(gender, ret_age_years, ret_age_months, guarantee, spouse_birth, emp_birth, survivor_pct, retro_months):
    # חישוב גיל עשרוני לדיוק בסיס המקדם
    exact_age = ret_age_years + (ret_age_months / 12)
    
    # 1. מקדמי בסיס (גברים פרישה 67, נשים 62)
    if gender == 'גבר':
        # בסיס גיל 67 הוא 181.49. כל חודש הקדמה מעלה את המקדם בכ-0.28 (3.45 לשנה)
        base = 181.49 + (67 - exact_age) * 3.45
    else:
        # בסיס אישה גיל 62 הוא 208.06.
        base = 208.06 + (62 - exact_age) * 3.7
    
    # 2. תוספת תקופת הבטחה
    guarantee_map = {0: 0, 60: 0.48, 120: 2.06, 180: 5.07, 240: 10.16}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    # 3. חישוב פער גילאים מדויק
    # הפרש בשנים (חיובי = בן זוג צעיר יותר)
    age_diff = (emp_birth - spouse_birth).days / 365.25
    
    # הצלבת פער גילאים לפי נספח ח': תוספת של כ-0.14 למקדם על כל שנת פער מעבר ל-3 שנים
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.142
    elif age_diff < -3:
        coeff -= (abs(age_diff) - 3) * 0.11
        
    # 4. התאמת שיעור שאירים (בסיס 60%)
    coeff += (survivor_pct - 60) * 0.155
    
    # 5. חודשי רטרו (0-3 חודשים)
    coeff *= (1 + (retro_months * 0.00185))
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה מדויק", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")
    st.info("חישוב גיל מדויק לפי שנים וחודשים - תקנון הפניקס יולי 2024")

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1960, 5, 15))
        gender = st.selectbox("מין", ["גבר", "אישה"])
        
        st.divider()
        st.header("📅 מועד פרישה")
        ret_date = st.date_input("תאריך פרישה מתוכנן", value=datetime(2027, 8, 1))
        
        # חישוב גיל מדויק במועד הפרישה
        rdiff = relativedelta(ret_date, emp_birth)
        st.success(f"גיל בפרישה: {rdiff.years} שנים ו-{rdiff.months} חודשים")
        
        st.divider()
        st.header("👫 בן/ת זוג ושאירים")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1964, 1, 1))
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ הגדרות מסלול")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו (0-3)", [0, 1, 2, 3], index=0)

    # חישוב המקדם (שולח שנים וחודשים בנפרד לדיוק)
    final_coeff = calculate_phoenix_pro_coeff(
        gender, rdiff.years, rdiff.months, guarantee, spouse_birth, emp_birth, survivor_pct, retro_months
    )
    
    # --- תצוגת תוצאות ---
    st.subheader("📊 דוח ריכוז נתוני פרישה")
    assets = st.number_input("צבירה פנסיונית כוללת (₪)", value=1000000.0, step=10000.0)
    pension = assets / final_coeff

    # חישוב גיל נוכחי להצגה
    age_now = relativedelta(datetime.now().date(), emp_birth)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("גיל הלקוח היום", f"{age_now.years}.{age_now.months}")
        st.caption("שנים וחודשים")
    with c2:
        st.metric("מקדם משוקלל", f"{final_coeff:.2f}")
    with c3:
        st.metric("קצבה ברוטו", f"₪{pension:,.0f}")

    st.divider()
    
    # פירוט מקצועי
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**פירוט השפעות על המקדם:**")
        st.write(f"- גיל פרישה מדויק: {rdiff.years}.{rdiff.months}")
        st.write(f"- חודשי רטרו: {retro_months}")
    with col_b:
        age_diff_val = (emp_birth - spouse_birth).days / 365.25
        st.write(f"- פער גילאים: {age_diff_val:.1f} שנים")
        st.write(f"- אחוז לשאיר: {survivor_pct}%")

if __name__ == "__main__":
    main()
