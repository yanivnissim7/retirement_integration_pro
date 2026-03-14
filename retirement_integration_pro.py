import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי מנורה מבטחים (תקנון יוני 2025) ---
def calculate_menora_pension_coeff(gender, exact_age, guarantee_months, survivor_pct, age_diff, retro_months, mgt_fees):
    # טבלת עוגנים - נספח ד' (מנורה יוני 2025)
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

    # תוספת הבטחה עם קיזוז מעל גיל 67
    eff_guarantee = guarantee_months
    if exact_age > 67 and guarantee_months > 0:
        eff_guarantee = max(0, guarantee_months - (exact_age - 67) * 12)
    
    guarantee_impact = (eff_guarantee / 240) * 11.60
    coeff = base + guarantee_impact
    
    # נספח ח' - פער גילאים
    if age_diff > 3:
        dynamic_factor = 0.25 + (max(0, exact_age - 65) * 0.018)
        coeff += (age_diff - 3) * dynamic_factor
    
    # שאירים ורטרו
    coeff += (survivor_pct - 60) * 0.19
    coeff *= (1 + (retro_months * 0.00355))
    
    # דמי ניהול
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return round(coeff, 2), int(eff_guarantee)

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")
    st.caption("מותאם לתקנון מנורה מבטחים מקיפה (יוני 2025)")

    # --- SIDEBAR ---
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

        # חישובים
        rdiff = relativedelta(ret_date, emp_birth)
        exact_age_ret = rdiff.years + (rdiff.months / 12)
        today_diff = relativedelta(date.today(), emp_birth)
        age_diff_val = (emp_birth - spouse_birth).days / 365.25
        
        target_coeff, eff_g = calculate_menora_pension_coeff(
            gender, exact_age_ret, guarantee, survivor_pct, age_diff_val, retro_months, mgt_fees
        )

        st.divider()
        st.subheader("📊 נתונים מחושבים")
        st.write(f"**גיל הלקוח כיום:** {today_diff.years}.{today_diff.months}")
        st.write(f"**גיל בפרישה:** {rdiff.years}.{rdiff.months}")
        
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border:2px solid #ff4b4b; text-align:center;">
            <h2 style="margin:0;">מקדם מטרה: {target_coeff:.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    # --- טבלת כספים ---
    st.subheader("💰 ריכוז קופות וצבירות")
    
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מקיפה', 'type': 'קצבתי', 'amount': 1000000.0}]

    col_btn1, col_btn2 = st.columns([1, 5])
    if col_btn1.button("➕ הוסף שורה"):
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
            fund['name'] = c1.text_input(f"תיאור הקופה", value=fund['name'], key=f"n_{i}")
            fund['type'] = c2.selectbox(f"סוג כסף", ["קצבתי", "הוני"], index=0 if fund.get('type') == 'קצבתי' else 1, key=f"t_{i}")
            fund['amount'] = c3.number_input(f"צבירה (₪)", value=fund['amount'], key=f"a_{i}")
            
            if fund['type'] == 'קצבתי':
                f_coeff = c4.number_input(f"מקדם", value=target_coeff, format="%.2f", key=f"c_{i}")
                total_pension += fund['amount'] / f_coeff if f_coeff > 0 else 0
                total_assets += fund['amount']
            else:
                c4.write(""); c4.caption("כסף הוני")
                total_capital += fund['amount']
                total_assets += fund['amount']
        st.markdown("---")

    # --- סיכום סופי ---
    st.subheader("📊 ריכוז תוצאות פרישה")
    res1, res2, res3 = st.columns(3)
    res1.metric("קצבה חודשית ברוטו", f"₪{total_pension:,.0f}")
    res2.metric("סה\"כ הון חד פעמי", f"₪{total_capital:,.0f}")
    res3.metric("סה\"כ צבירה בתיק", f"₪{total_assets:,.0f}")

if __name__ == "__main__":
    main()
