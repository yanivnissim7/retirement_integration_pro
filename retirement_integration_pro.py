import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי מנורה מבטחים (מהדורת יוני 2025) ---
def calculate_menora_pension_coeff(gender, exact_age, guarantee_months, survivor_pct, age_diff, retro_months, mgt_fees):
    # 1. טבלת עוגנים - מקדם בסיס (לפי נספח ד' - מנורה יוני 2025)
    anchors = {
        60: 172.50, 61: 176.20, 62: 180.10, 63: 184.20, 64: 188.50,
        65: 193.10, 66: 197.90, 67: 203.00, 68: 208.40, 69: 214.10, 70: 220.10
    }
    
    age_floor = int(exact_age)
    age_ceil = age_floor + 1
    
    if age_floor in anchors and age_ceil in anchors:
        base = anchors[age_floor] + (anchors[age_ceil] - anchors[age_floor]) * (exact_age - age_floor)
    else:
        base = 203.00 + (exact_age - 67) * 5.4

    # 2. תוספת הבטחה (כ-0.0483 לחודש) עם קיזוז מעל גיל 67
    eff_guarantee = guarantee_months
    if exact_age > 67 and guarantee_months > 0:
        eff_guarantee = max(0, guarantee_months - (exact_age - 67) * 12)
    
    guarantee_impact = (eff_guarantee / 240) * 11.60
    coeff = base + guarantee_impact
    
    # 3. נספח ח' - פער גילאים (בסיס 3 שנים)
    if age_diff > 3:
        dynamic_factor = 0.25 + (max(0, exact_age - 65) * 0.018)
        coeff += (age_diff - 3) * dynamic_factor
    
    # 4. התאמה לשאירים (בסיס 60%)
    coeff += (survivor_pct - 60) * 0.19
    
    # 5. חודשי רטרו (כ-0.355% לכל חודש לפי תקנון מנורה)
    coeff *= (1 + (retro_months * 0.00355))
    
    # 6. דמי ניהול מהקצבה
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return round(coeff, 2), int(eff_guarantee)

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")
    st.caption("מותאם לתקנון מנורה מבטחים מקיפה (יוני 2025)")

    # --- SIDEBAR: נתונים ובחירות ---
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=date(1965, 3, 26))
        gender = st.selectbox("מין", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה (תחילת קצבה)", value=date(2032, 3, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג ושאירים")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=date(1970, 1, 1))
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ הגדרות מסלול")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו (תשלום למפרע)", [0, 1, 2, 3], index=0)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)

        # --- חישובים אקטואריים ---
        rdiff = relativedelta(ret_date, emp_birth)
        exact_age_ret = rdiff.years + (rdiff.months / 12)
        
        today_diff = relativedelta(date.today(), emp_birth)
        age_diff = (emp_birth - spouse_birth).days / 365.25
        
        target_coeff, eff_g = calculate_menora_pension_coeff(
            gender, exact_age_ret, guarantee, survivor_pct, age_diff, retro_months, mgt_fees
        )

        st.divider()
        st.subheader("📊 נתונים מחושבים")
        st.write(f"**גיל הלקוח כיום:** {today_diff.years}.{today_diff.months}")
        st.write(f"**גיל בפרישה:** {rdiff.years}.{rdiff
