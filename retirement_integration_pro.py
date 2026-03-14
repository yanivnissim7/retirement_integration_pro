import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי "אפקט" - כיול סופי לפניקס 2024 ---
def calculate_accurate_phoenix_coeff(gender, exact_age, guarantee, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees):
    # טבלת עוגנים (גבר, הבטחה 0, שאירים 60%, ללא דמי ניהול)
    # הכיול כאן מחמיר יותר כדי להתאים לנתונים שציינת
    anchors = {
        60: 172.50, 61: 176.20, 62: 180.10, 63: 184.20, 64: 188.50,
        65: 193.10, 66: 197.90, 67: 203.00, 68: 208.40, 69: 214.10, 70: 220.10
    }
    
    age_floor = int(exact_age)
    age_ceil = age_floor + 1
    
    if age_floor in anchors and age_ceil in anchors:
        base = anchors[age_floor] + (anchors[age_ceil] - anchors[age_floor]) * (exact_age - age_floor)
    else:
        base = 203.00 + (exact_age - 67) * 5.5

    # תוספת הבטחה - ליניארית (כ-0.048 נקודות לחודש)
    eff_guarantee = guarantee
    if exact_age > 67 and guarantee > 0:
        eff_guarantee = max(0, guarantee - (exact_age - 67) * 12)
    
    guarantee_impact = (eff_guarantee / 240) * 11.60
    coeff = base + guarantee_impact
    
    # נספח ח' (פער גילאים)
    age_diff = (emp_birth - spouse_birth).days / 365.25
    if age_diff > 3:
        dynamic_factor = 0.25 + (max(0, exact_age - 65) * 0.018)
        coeff += (age_diff - 3) * dynamic_factor
    
    # שאירים, רטרו ודמי ניהול
    coeff += (survivor_pct - 60) * 0.19
    coeff *= (1 + (retro_months * 0.00355))
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return round(coeff, 2)

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 מערכת תכנון פרישה - אפקט")
    
    # אתחול Session State בצורה בטוחה
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'קרן פנסיה', 'type': 'קצבתי', 'amount': 1000000.0}]

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=date(1965, 3, 26))
        gender = st.selectbox("מין", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה", value=date(2027, 3, 26)) # הגדרתי ל-2027 כדי להגיע לגיל 62
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=date(1970, 1, 1))
        survivor_pct = st.select_slider("אחוז לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ מסלול")
        guarantee = st.selectbox("הבטחה", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=0)
        mgt_fees = st.number_input("דמי ניהול (%)", value=0.3, step=0.1)

        # חישוב גיל בפרישה
        rdiff = relativedelta(ret_date, emp_birth)
        exact_age = rdiff.years + (rdiff.months / 12)
        
        current_coeff = calculate_accurate_phoenix_coeff(
            gender, exact_age, guarantee, spouse_birth, emp_birth, survivor_pct, retro_months, mgt_fees
        )
        
        st.divider()
        st.subheader("📌 נתוני חישוב")
        st.write(f"**גיל פרישה:** {rdiff.years} שנים ו-{rdiff.months} חודשים")
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border:2px solid #ff4b4b; text-align:center;">
            <h2 style="color:#1f1f1f; margin:0;">{current_coeff:.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    # --- טבלת כספים ---
    st.subheader("💰 ריכוז קופות וצבירות")
    
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("➕ הוסף שורה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0})
            st.rerun()
    with col_btn2:
        if st.button("🗑️ נקה הכל"):
            st.session_state.funds = [{'name': 'קרן פנסיה', 'type': 'קצבתי', 'amount': 0.0}]
            st.rerun()

    total_pension = 0.0; total_capital = 0.0; total_assets = 0.0

    # תצוגת הטבלה
    for i, fund in enumerate(st.session_state.funds):
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
            with c1: fund['name'] = st.text_input(f"תיאור", value=fund['name'], key=f"n_{i}")
            with c2: fund['type'] = st.selectbox(f"סוג", ["קצבתי", "הוני"], index=0 if fund['type'] == 'קצבתי' else 1, key=f"t_{i}")
            with c3: fund['amount'] = st.number_input(f"צבירה", value=fund['amount'], key=f"a_{i}")
            
            if fund['type'] == 'קצבתי':
                with c4:
                    # שימוש ב-value ישיר ללא ניהול Session State מורכב מדי למקדם
                    coeff_val = st.number_input(f"מקדם", value=float(current_coeff), format="%.2f", key=f"c_{i}")
                total_pension += fund['amount'] / coeff_val if coeff_val > 0 else 0
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
