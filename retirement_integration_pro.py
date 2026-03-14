import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים "רמת פניקס" (סנכרון מלא: רטרו, שואירים, דמי ניהול) ---
def calculate_accurate_phoenix_coeff(gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees):
    # 1. בסיס מקדם (גבר גיל 65 בסיס 187.97)
    if gender == 'גבר':
        base = 187.97 + (65 - exact_age) * 3.65
    else:
        base = 208.06 + (64 - exact_age) * 3.8
    
    # 2. תוספת תקופת הבטחה (240 חודשים)
    guarantee_map = {0: 0, 60: 0.52, 120: 2.25, 180: 5.65, 240: 11.45}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    # 3. פער גילאים (נספח ח')
    age_diff = (emp_birth - spouse_birth).days / 365.25
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.195
    elif age_diff < -3:
        coeff -= (abs(age_diff) - 3) * 0.12
    
    # 4. התאמת שיעור שאירים (קריטי!)
    # הבסיס בלוחות ח' הוא לרוב 60%. תוספת ל-100% מעלה את המקדם משמעותית.
    # המכפיל כאן מותאם לסטייה שראינו בסימולטור של הפניקס
    survivor_adjustment = (survivor_pct - 60) * 0.172
    coeff += survivor_adjustment
    
    # 5. תיקון רטרו (0-3 חודשים)
    retro_factor = 1 + (retro_months * 0.0031) 
    coeff *= retro_factor
    
    # 6. העמסת דמי ניהול מהקצבה (0.3% / 0.5%)
    mgt_fee_factor = 1 / (1 - (mgt_fees / 100))
    coeff *= mgt_fee_factor
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה מלא", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")
    st.info("המנוע כולל כעת את כל פרמטרי נספח ח' - כולל אחוז שאיר ורטרו")

    # --- SIDEBAR - כל הפרמטרים כאן ---
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1961, 3, 26))
        gender = st.selectbox("מין העמית", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה", value=datetime(2026, 3, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג ושאירים")
        spouse_gender = st.selectbox("מין בן/ת הזוג", ["אישה", "גבר"], index=0 if gender == "גבר" else 1)
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1971, 7, 26))
        # הפרמטר שחזר:
        survivor_pct = st.select_slider("אחוז קצבה לשאיר בפטירה", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ מסלול, רטרו וניהול")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו (0-3)", [0, 1, 2, 3], index=3)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)

    # חישוב גיל
    rdiff = relativedelta(ret_date, emp_birth)
    exact_age = rdiff.years + (rdiff.months / 12)
    
    # הפעלת המנוע
    final_coeff = calculate_accurate_phoenix_coeff(
        gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees
    )
    
    # תצוגת תוצאות
    assets = st.number_input("צבירה פנסיונית כוללת (₪)", value=1000000.0, step=10000.0)
    pension = assets / final_coeff

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("מקדם משוקלל (אפקט)", f"{final_coeff:.2f}")
    with c2:
        st.metric("קצבה חודשית ברוטו", f"₪{pension:,.0f}")
    with c3:
        st.metric("קצבת שאיר", f"₪{pension * (survivor_pct/100):,.0f}")

    st.write("---")
    # טבלת סיכום
    age_diff_val = (emp_birth - spouse_birth).days / 365.25
    summary = {
        "פרמטר": ["גיל פרישה", "פער גילאים", "אחוז לשאיר", "חודשי רטרו", "דמי ניהול"],
        "ערך": [f"{rdiff.years}.{rdiff.months}", f"{age_diff_val:.1f} שנים", f"{survivor_pct}%", f"{retro_months}", f"{mgt_fees}%"]
    }
    st.table(pd.DataFrame(summary))

if __name__ == "__main__":
    main()
