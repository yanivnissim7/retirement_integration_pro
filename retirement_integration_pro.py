import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי רב-גילאי "אפקט" ---
def calculate_accurate_phoenix_coeff(gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees):
    # 1. טבלת עוגנים אקטוארית (גבר, נספח ח', לוחות 2024)
    # המקדם עולה בצורה מעריכית ככל שהגיל עולה
    if gender == 'גבר':
        if exact_age < 65:
            base = 190.58 - (65 - exact_age) * 3.7
        elif exact_age <= 70:
            # בגילאים אלו (65-70) השיפוע גדל ל-4.35 בשנה
            base = 190.58 + (exact_age - 65) * 4.35
        else:
            # מעל גיל 70 השיפוע מאיץ עוד יותר
            base = 212.33 + (exact_age - 70) * 5.1
    else:
        base = 210.50 + (exact_age - 62) * 4.2

    # 2. מנגנון קיזוז הבטחה (גיל 67 + 20 שנה = גיל 87)
    effective_guarantee = guarantee
    if exact_age > 67 and guarantee > 0:
        over_age_months = (exact_age - 67) * 12
        effective_guarantee = max(0, guarantee - over_age_months)
    
    # 3. תוספת הבטחה (משתנה לפי גיל - ככל שזקנים יותר, ההבטחה "זולה" יותר אקטוארית)
    guarantee_impact = (effective_guarantee / 240) * 11.60
    if exact_age > 70: guarantee_impact *= 0.85 # התאמה לגיל מבוגר
    
    coeff = base + guarantee_impact
    
    # 4. פער גילאים (נספח ח') - השפעה דרמטית בגיל מבוגר
    age_diff = (emp_birth - spouse_birth).days / 365.25
    if age_diff > 3:
        # פקטור נספח ח' גדל עם גיל הפורש
        dynamic_age_factor = 0.248 + (max(0, exact_age - 65) * 0.02)
        coeff += (age_diff - 3) * dynamic_age_factor
    
    # 5. שיעור שאירים (בסיס 60%)
    coeff += (survivor_pct - 60) * 0.19
    
    # 6. רטרו (0.355% לחודש)
    coeff *= (1 + (retro_months * 0.00355))
    
    # 7. דמי ניהול (0.3%)
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return coeff, effective_guarantee

def main():
    st.set_page_config(page_title="אפקט - תכנון פרישה רב-גילאי", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 מערכת תכנון פרישה - אפקט")
    
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1955, 3, 26)) # יליד 55 לבדיקה
        
        age_today = relativedelta(datetime.now(), emp_birth)
        st.info(f"📅 **גיל הלקוח כיום:** {age_today.years} שנים ו-{age_today.months} חודשים")
        
        gender = st.selectbox("מין", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה", value=datetime(2025, 6, 1))
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1965, 1, 1))
        survivor_pct = st.select_slider("אחוז לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ מסלול")
        guarantee = st.selectbox("הבטחה מבוקשת", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=0)
        mgt_fees = st.number_input("דמי ניהול (%)", value=0.3, step=0.1)

        # חישוב
        rdiff = relativedelta(ret_date, emp_birth)
        exact_age_at_ret = rdiff.years + (rdiff.months / 12)
        current_coeff, final_guarantee = calculate_accurate_phoenix_coeff(
            gender, exact_age_at_ret, guarantee, "אישה", spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees
        )
        
        st.divider()
        st.subheader("📌 מקדם מטרה (אפקט)")
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; border:2px solid #ff4b4b; text-align:center;">
            <h1 style="color:#1f1f1f; margin:0;">{current_coeff:.2f}</h1>
            <p style="margin:5px 0;">גיל פרישה: {rdiff.years}.{rdiff.months}</p>
            {"<p style='color:red; font-size:0.8em;'>⚠️ הבטחה קוזזה ל-" + str(int(final_guarantee)) + " חודשים</p>" if final_guarantee < guarantee else ""}
        </div>
        """, unsafe_allow_html=True)

    # --- טבלת כספים ---
    st.subheader("💰 ריכוז קופות וצבירות")
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'קרן פנסיה', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': current_coeff}]

    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("➕ הוסף שורה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': current_coeff})
    with col_btn2:
        if st.button("🗑️ נקה הכל"):
            st.session_state.funds = []; st.rerun()

    total_pension = 0.0
    total_assets = 0.0
    total_capital = 0.0

    for i, fund in enumerate(st.session_state.funds):
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
            with c1: fund['name'] = st.text_input(f"תיאור", value=fund['name'], key=f"n_{i}")
            with c2: fund['type'] = st.selectbox(f"סוג", ["קצבתי", "הוני"], index=0 if fund['type'] == 'קצבתי' else 1, key=f"t_{i}")
            with c3: fund['amount'] = st.number_input(f"צבירה", value=fund['amount'], key=f"a_{i}")
            
            if fund['type'] == 'קצבתי':
                with c4: fund['coeff'] = st.number_input(f"מקדם", value=fund['coeff'], format="%.2f", key=f"c_{i}")
                p_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                total_pension += p_val
                total_assets += fund['amount']
            else:
                with c4: st.write(""); st.caption("סכום הוני")
                total_capital += fund['amount']
        st.markdown("---")

    # סיכום
    res1, res2, res3 = st.columns(3)
    res1.metric("קצבה חודשית ברוטו", f"₪{total_pension:,.0f}")
    res2.metric("סה\"כ הון חד פעמי", f"₪{total_capital:,.0f}")
    res3.metric("סה\"כ שווי תיק", f"₪{(total_assets + total_capital):,.0f}")

if __name__ == "__main__":
    main()
