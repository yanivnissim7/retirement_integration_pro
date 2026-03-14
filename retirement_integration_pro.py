import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- נתוני יסוד 2026 ---
SAL_PTUR_MAX = 976005 
MAX_WAGE_FOR_EXEMPT = 13750 

def fmt_num(num): return f"₪{float(num):,.0f}"

def calculate_income_tax(monthly_income, credit_points=2.25):
    brackets = [(7010, 0.10), (10060, 0.14), (16150, 0.20), (22440, 0.31), (46690, 0.35), (float('inf'), 0.47)]
    tax, prev_bracket = 0, 0
    marginal_rate = 0.10
    for bracket, rate in brackets:
        if monthly_income > prev_bracket:
            taxable_in_bracket = min(monthly_income, bracket) - prev_bracket
            tax += taxable_in_bracket * rate
            marginal_rate = rate
            prev_bracket = bracket
        else: break
    return max(0, tax - (credit_points * 250)), marginal_rate

def main():
    st.set_page_config(page_title="אפקט - תכנון פריסה למס הכנסה", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח", value="")
        ret_date = st.date_input("תאריך פרישה", value=date(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=33.4)
        
        st.divider()
        st.header("💰 מענקים")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=968000)
        salary_for_exempt = st.number_input("שכר קובע לפטור (לפי 161)", value=13750)
        past_exempt_grants = st.number_input("מענקים פטורים בעבר", value=0)

    # --- חישוב פטור וחייב (התשובה לשאלתך) ---
    # פטור לפי ותק ותקרה
    annual_exempt_limit = min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT)
    total_exempt_amount = min(total_grant_bruto, seniority * annual_exempt_limit)
    taxable_grant_amount = total_grant_bruto - total_exempt_amount

    st.markdown(f"<h1>תכנון פרישה אסטרטגי - {client_name}</h1>", unsafe_allow_html=True)

    # הצגת נתוני פטור/חייב בולטים
    st.subheader("📋 סיכום מענקי פרישה (טופס 161)")
    c1, c2, c3 = st.columns(3)
    c1.metric("סך המענק ברוטו", fmt_num(total_grant_bruto))
    c2.success(f"סכום פטור ממס: {fmt_num(total_exempt_amount)}")
    c3.error(f"סכום חייב במס (לפריסה): {fmt_num(taxable_grant_amount)}")

    st.divider()

    # --- ריכוז קופות ---
    st.subheader("1. קצבה חזויה מהקופות")
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10}]

    if st.button("➕ הוסף קופה"):
        st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0})
        st.rerun()

    total_pension_monthly = 0.0
    for i, fund in enumerate(st.session_state.funds):
        col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
        fund['name'] = col1.text_input(f"שם קופה {i+1}", fund.get('name',''), key=f"n_{i}")
        fund['type'] = col2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
        fund['amount'] = col3.number_input("צבירה ₪", value=float(fund.get('amount',0)), key=f"a_{i}")
        if fund['type'] == 'קצבתי':
            fund['coeff'] = col4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
            total_pension_monthly += fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0

    # --- פריסת מס ---
    st.divider()
    st.subheader("2. דוח פריסת מס להגשה למס הכנסה")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        other_inc_monthly = st.number_input("שכר צפוי/פנסיה נוספת (ברוטו חודשי):", value=0)
        num_years = st.slider("מספר שנות פריסה:", 1, 6, 6)
    with col_p2:
        is_after_oct = ret_date.month >= 10
        start_year = st.selectbox("שנת תחילת פריסה:", [ret_date.year, ret_date.year + 1] if is_after_oct else [ret_date.year])

    # טבלת פריסה
    ann_taxable_part = taxable_grant_amount / num_years
    spread_rows = []
    
    for i in range(num_years):
        yr = start_year + i
        # שכר צפוי שנתי + קצבה שנתית
        existing_income_annual = (total_pension_monthly + other_inc_monthly) * 12
        # ברוטו שנתי כולל לפריסה (מענק חייב שנתי + הכנסה קיימת)
        total_combined_annual = existing_income_annual + ann_taxable_part
        
        # חישוב מס
        tax_total, m_rate = calculate_income_tax(total_combined_annual / 12, credit_points)
        tax_on_grant_yr = (tax_total - calculate_income_tax(existing_income_annual / 12, credit_points)[0]) * 12
        
        spread_rows.append({
            "שנה": yr,
            "שכר וקצבה צפויה (שנתי)": fmt_num(existing_income_annual),
            "חלק מענק חייב (שנתי)": fmt_num(ann_taxable_part),
            "סך ברוטו שנתי לדו\"ח": fmt_num(total_combined_annual),
            "מס משוער על המענק": fmt_num(max(0, tax_on_grant_yr)),
            "מדרגת מס שולית": f"{m_rate*100:.0f}%"
        })

    st.table(pd.DataFrame(spread_rows))

    # --- חתימה ---
    st.markdown(f"""
        <div style="margin-top: 50px; border-top: 2px solid #000; padding-top: 10px;">
            <p><b>חתימת הלקוח:</b> _________________ | <b>תאריך:</b> {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
