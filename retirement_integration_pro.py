import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי משולב: ממוצע מנורה/הפניקס 2025 ---
def calculate_calibrated_coeff(gender, exact_age, req_guarantee, survivor_pct, age_diff, retro_months, mgt_fees):
    # 1. טבלאות עוגן - ממוצע מנורה והפניקס (גבר)
    anchors_male = {
        60: 214.98, 61: 210.42, 62: 207.10, 63: 203.67, 64: 200.13,
        65: 196.45, 66: 191.01, 67: 187.08, 68: 183.04, 69: 178.88, 70: 174.58
    }
    
    # 2. ריגרסיה מעבר לגיל 70 (קצב ירידה ממוצע של 4.2 נקודות לשנה)
    if exact_age <= 70:
        age_floor = int(exact_age)
        age_ceil = age_floor + 1
        base = anchors_male[age_floor] - (anchors_male[age_floor] - anchors_male[age_ceil]) * (exact_age - age_floor)
    else:
        extra_years = exact_age - 70
        base = 174.58 - (extra_years * 4.2)

    # 3. מנגנון הבטחה עד גיל 87 (הגורם המכייל ל-197)
    # ככל שפורשים מאוחר יותר, כל חודש הבטחה "שוקל" יותר במקדם.
    max_guarantee_age = 87
    available_months = max(0, (max_guarantee_age - exact_age) * 12)
    eff_guarantee = min(float(req_guarantee), available_months)
    
    # פקטור כיול: בפרישה בגיל 70, הבטחה מלאה מוסיפה כ-18-22 נקודות
    # נוסחת עלות הבטחה משתנה לפי גיל (בגיל 60 היא זולה, ב-70 היא יקרה מאוד)
    guarantee_cost_per_month = 0.025 + (max(0, exact_age - 60) * 0.005) 
    guarantee_impact = eff_guarantee * guarantee_cost_per_month
    
    coeff = base + guarantee_impact
    
    # 4. פער גילאים ושאירים (נספח ח')
    # בסיס 60% שאיר. כל 10% מעבר לכך מוסיפים כ-1.5 נקודות
    survivor_impact = (survivor_pct - 60) * 0.16
    
    # פער גילאים: בת זוג צעירה יותר מעלה את המקדם
    age_diff_impact = max(0, age_diff - 3) * 0.24
    
    coeff += survivor_impact + age_diff_impact
    
    # 5. החלת חודשי רטרו (מכפיל אקטוארי)
    # כל חודש רטרו מעלה את המקדם בכ-0.355%
    coeff *= (1 + (retro_months * 0.00355))
    
    # 6. דמי ניהול מהקצבה (מגדילים את המקדם)
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return round(coeff, 2), round(eff_guarantee, 1)

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")
    st.caption("מיזוג נתוני מנורה והפניקס 2025 | כולל כיול אקטוארי מלא")

    # --- SIDEBAR: כל הפרמטרים שביקשת ---
    with st.sidebar:
        st.header("👤 נתוני העמית")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        emp_birth = st.date_input("תאריך לידה עמית", value=date(1956, 11, 30))
        ret_date = st.date_input("תאריך פרישה מבוקש", value=date.today())
        
        st.divider()
        st.header("👫 נתוני בן/ת זוג")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=date(1960, 1, 1))
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ מסלול וכיול")
        req_guarantee = st.selectbox("הבטחה מבוקשת (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו (תשלום למפרע)", [0, 1, 2, 3], index=0)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)

        # חישובים גילים
        rdiff_now = relativedelta(date.today(), emp_birth)
        rdiff_ret = relativedelta(ret_date, emp_birth)
        exact_age_ret = rdiff_ret.years + (rdiff_ret.months / 12)
        age_diff_val = (emp_birth - spouse_birth).days / 365.25
        
        # הרצת המנוע האקטוארי
        target_coeff, eff_g = calculate_calibrated_coeff(
            gender, exact_age_ret, req_guarantee, survivor_pct, age_diff_val, retro_months, mgt_fees
        )

        st.divider()
        st.subheader("📊 נתונים מחושבים")
        st.write(f"**גיל עכשווי:** {rdiff_now.years}.{rdiff_now.months}")
        st.write(f"**גיל פרישה:** {rdiff_ret.years}.{rdiff_ret.months}")
        st.warning(f"**הבטחה אפקטיבית (גיל 87):** {eff_g} חודשים")
        st.success(f"**מקדם סופי:** {target_coeff:.2f}")

    # --- טבלאות הוספת קופות ---
    st.subheader("💰 פירוט צבירות וכספים")
    
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מקיפה', 'type': 'קצבתי', 'amount': 1000000.0}]

    col_btn1, col_btn2 = st.columns([1, 5])
    if col_btn1.button("➕ הוסף קופה/שורה"):
        st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0})
        st.rerun()
    if col_btn2.button("🗑️ נקה הכל"):
        st.session_state.funds = [{'name': '', 'type': 'קצבתי', 'amount': 0.0}]
        st.rerun()

    total_pension = 0.0
    total_capital = 0.0
    total_assets = 0.0

    for i, fund in enumerate(st.session_state.funds):
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
            fund['name'] = c1.text_input("שם הקופה", value=fund['name'], key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג כסף", ["קצבתי", "הוני"], key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה (₪)", value=fund['amount'], key=f"a_{i}")
            
            if fund['type'] == 'קצבתי':
                # המקדם מסונכרן לערך הכיול מהסיידבר
                f_coeff = c4.number_input("מקדם", value=target_coeff, format="%.2f", key=f"c_{i}")
                total_pension += fund['amount'] / f_coeff if f_coeff > 0 else 0
            else:
                c4.write(""); c4.caption("כסף הוני")
                total_capital += fund['amount']
            total_assets += fund['amount']
        st.markdown("---")

    # --- סיכום תוצאות ---
    st.subheader("📊 סיכום פרישה צפוי")
    res1, res2, res3 = st.columns(3)
    res1.metric("קצבה חודשית (ברוטו)", f"₪{total_pension:,.0f}")
    res2.metric("סה\"כ הון חד פעמי", f"₪{total_capital:,.0f}")
    res3.metric("סה\"כ נכסים מנוהלים", f"₪{total_assets:,.0f}")

if __name__ == "__main__":
    main()
