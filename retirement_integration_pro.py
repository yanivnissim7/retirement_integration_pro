import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים "אפקט" - כיול סופי ---
def calculate_accurate_phoenix_coeff(gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees):
    if gender == 'גבר':
        base = 191.28 + (65 - exact_age) * 3.72
    else:
        base = 210.50 + (62 - exact_age) * 3.75
    
    guarantee_map = {0: 0, 60: 0.55, 120: 2.30, 180: 5.75, 240: 11.60}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    age_diff = (emp_birth - spouse_birth).days / 365.25
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.248
    elif age_diff < -3:
        coeff -= (abs(age_diff) - 3) * 0.13
    
    coeff += (survivor_pct - 60) * 0.182
    retro_factor = 1 + (retro_months * 0.00355) 
    coeff *= retro_factor
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return coeff

def main():
    st.set_page_config(page_title="אפקט - מערכת תכנון פרישה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 מערכת תכנון פרישה - אפקט")
    
    # --- SIDEBAR - פרמטרים אקטואריים ---
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1961, 3, 26))
        gender = st.selectbox("מין העמית", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה", value=datetime(2026, 3, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_gender = st.selectbox("מין בן/ת הזוג", ["אישה", "גבר"], index=0 if gender == "גבר" else 1)
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1971, 7, 26))
        survivor_pct = st.select_slider("אחוז לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ הגדרות מסלול")
        guarantee = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=3)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)

        # --- הנתון הצדי שביקשת ---
        st.divider()
        rdiff = relativedelta(ret_date, emp_birth)
        exact_age = rdiff.years + (rdiff.months / 12)
        current_calc_coeff = calculate_accurate_phoenix_coeff(
            gender, exact_age, guarantee, spouse_gender, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees
        )
        
        st.subheader("📌 מקדם מטרה (אפקט)")
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; border:2px solid #ff4b4b; text-align:center;">
            <h1 style="color:#1f1f1f; margin:0;">{current_calc_coeff:.2f}</h1>
            <small>הזן נתון זה בטבלה עבור הקופה הרלוונטית</small>
        </div>
        """, unsafe_allow_html=True)

    # --- מרכז המסך - ניהול קופות וכספים ---
    st.subheader("💰 ריכוז קופות וצבירות")
    
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'קרן פנסיה', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': current_calc_coeff}]

    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': current_calc_coeff})
    with col_btn2:
        if st.button("🗑️ נקה הכל"):
            st.session_state.funds = []
            st.rerun()

    total_pension = 0.0
    total_assets = 0.0

    # תצוגת הקופות בפורמט נוח
    for i, fund in enumerate(st.session_state.funds):
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 1])
            with c1:
                fund['name'] = st.text_input(f"שם הקופה", value=fund['name'], key=f"n_{i}")
            with c2:
                fund['type'] = st.selectbox(f"סוג", ["קצבתי", "הוני"], index=0 if fund['type'] == 'קצבתי' else 1, key=f"t_{i}")
            with c3:
                fund['amount'] = st.number_input(f"צבירה (₪)", value=fund['amount'], step=10000.0, key=f"a_{i}")
            with c4:
                # כאן המשתמש מזין את המקדם שמופיע לו בצד
                fund['coeff'] = st.number_input(f"מקדם", value=fund['coeff'], format="%.2f", key=f"c_{i}")
            with c5:
                p_val = fund['amount'] / fund['coeff'] if fund['type'] == 'קצבתי' and fund['coeff'] > 0 else 0
                st.write("**קצבה צפויה:**")
                st.write(f"₪{p_val:,.0f}")
                total_pension += p_val
                total_assets += fund['amount']

    st.markdown("---")
    
    # סיכום סופי
    res1, res2, res3 = st.columns(3)
    res1.metric("סה\"כ קצבה חודשית (ברוטו)", f"₪{total_pension:,.0f}")
    res2.metric("סה\"כ הון מנוהל", f"₪{total_assets:,.0f}")
    avg_coeff = total_assets / total_pension if total_pension > 0 else 0
    res3.metric("מקדם משוקלל לתיק", f"{avg_coeff:.2f}")

if __name__ == "__main__":
    main()
