import streamlit as st
import pandas as pd  # התיקון כאן
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים "רמת פניקס" (סנכרון מלא 2024) ---
def calculate_accurate_phoenix_coeff(gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees):
    # 1. בסיס מקדם מדויק (לפי גיל פרישה)
    if gender == 'גבר':
        # בסיס גיל 65 הוא 187.97. כל חודש הקדמה/איחור משנה בכ-0.3
        base = 187.97 + (65 - exact_age) * 3.65
    else:
        # בסיס אישה גיל 64 הוא 200.82
        base = 200.82 + (64 - exact_age) * 3.8
    
    # 2. תוספת תקופת הבטחה
    guarantee_map = {0: 0, 60: 0.52, 120: 2.25, 180: 5.65, 240: 11.45}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    # 3. פער גילאים ומין בן הזוג
    age_diff = (emp_birth - spouse_birth).days / 365.25
    
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.192
    elif age_diff < -3:
        coeff -= (abs(age_diff) - 3) * 0.12
    
    if gender == spouse_gender:
        coeff *= 1.01 
        
    # 4. התאמת שיעור שאירים
    coeff += (survivor_pct - 60) * 0.168
    
    # 5. חודשי רטרו
    coeff *= (1 + (retro_months * 0.00195))
    
    # 6. העמסת דמי ניהול מהקצבה
    mgt_fee_factor = 1 / (1 - (mgt_fees / 100))
    coeff *= mgt_fee_factor
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה מלא", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")

    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1961, 3, 26))
        gender = st.selectbox("מין העמית", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה מבוקש", value=datetime(2026, 3, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג ושאירים")
        spouse_gender = st.selectbox("מין בן/ת הזוג", ["אישה", "גבר"], index=0 if gender == "גבר" else 1)
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1971, 7, 26))
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ הגדרות מסלול ורטרו")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו (0-3)", [0, 1, 2, 3], index=0)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)

    rdiff = relativedelta(ret_date, emp_birth)
    exact_age = rdiff.years + (rdiff.months / 12)
    
    final_coeff = calculate_accurate_phoenix_coeff(
        gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees
    )
    
    st.subheader("📊 סיכום נתוני פרישה")
    assets = st.number_input("צבירה פנסיונית כוללת (₪)", value=1000000.0, step=10000.0)
    pension = assets / final_coeff

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("מקדם משוקלל", f"{final_coeff:.2f}")
    with c2:
        st.metric("קצבה חודשית ברוטו", f"₪{pension:,.0f}")
    with c3:
        st.metric("קצבת שאיר", f"₪{pension * (survivor_pct/100):,.0f}")

    st.write("---")
    st.write("**פירוט לחישוב:**")
    summary_data = {
        "פרמטר": ["פער גילאים", "העמסה", "הבטחה", "גיל פרישה"],
        "ערך": [f"{(emp_birth - spouse_birth).days/365.25:.1f} שנים", f"{mgt_fees}%", f"{guarantee} חודשים", f"{rdiff.years}.{rdiff.months}"]
    }
    st.table(pd.DataFrame(summary_data))

if __name__ == "__main__":
    main()
