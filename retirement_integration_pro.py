import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

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
    st.set_page_config(page_title="אפקט - תכנון פרישה למס הכנסה", layout="wide")

    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 נתוני יסוד")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        ret_date = st.date_input("תאריך פרישה", value=date(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=33.4)
        
        st.divider()
        st.header("💰 מענקים")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=968000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("סך מענקים פטורים בעבר", value=0)

    # --- 1. ריכוז קופות (מנגנון המקדמים) ---
    st.subheader("1. ריכוז קופות וצבירות")
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'קופה 1', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10}]

    if st.button("➕ הוסף קופה"):
        st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0})
        st.rerun()

    total_pension_monthly = 0.0
    for i, fund in enumerate(st.session_state.funds):
        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
        fund['name'] = c1.text_input(f"שם קופה {i+1}", fund.get('name',''), key=f"n_{i}")
        fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
        fund['amount'] = c3.number_input("צבירה", value=float(fund.get('amount',0)), key=f"a_{i}")
        if fund['type'] == 'קצבתי':
            fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
            total_pension_monthly += fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0

    st.divider()

    # --- 2. חישוב קיבוע וסל פטור ---
    actual_exempt_now = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant = total_grant_bruto - actual_exempt_now
    reduction = ((actual_exempt_now + past_exempt_grants) * 1.35) * (32/seniority if seniority > 32 else 1)
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction)
    
    st.subheader("2. קיבוע זכויות (סל הפטור)")
    pct_to_pension = st.select_slider("ניצול פטור לטובת הקצבה (0% = הכל להון):", options=range(0,101,10), value=0)
    mon_exempt_val = (rem_sal_base / 180) * (pct_to_pension / 100)
    
    st.info(f"פטור חודשי על הקצבה: {fmt_num(mon_exempt_val)} | יתרת הון פטורה: {fmt_num(rem_sal_base * (1 - pct_to_pension/100))}")

    # --- 3. מודול פריסה מתקדם ---
    st.subheader("3. תכנון פריסת מס (לדו\"ח שנתי)")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        spread_dir = st.radio("כיוון פריסה:", ["קדימה (שנים הבאות)", "אחורה (שנים קודמות)"], index=0)
        is_after_oct = ret_date.month >= 10
        start_year_opt = [ret_date.year, ret_date.year + 1] if is_after_oct else [ret_date.year]
        start_year = st.selectbox("שנת תחילת פריסה:", start_year_opt)
        
        if not is_after_oct and start_year > ret_date.year:
            st.warning("שים לב: דחיית פריסה בפרישה שלפני 1.10 מקצרת את הפריסה ל-5 שנים.")
            max_spread = 5
        else:
            max_spread = 6
        
        num_years = st.slider("מספר שנות פריסה (כולל שנת ההתחלה):", 1, max_spread, max_spread)

    with col_v2:
        other_inc_monthly = st.number_input("הכנסה חודשית נוספת צפויה (שכר/פנסיה נוספת):", value=0)
        credit_pts_spread = st.number_input("נקודות זיכוי בפריסה:", value=credit_points)

    # חישוב טבלת פריסה
    ann_grant_part = taxable_grant / num_years
    rows = []
    
    for i in range(num_years):
        yr = start_year + i if spread_dir.startswith("קדימה") else start_year - i
        
        # הכנסה בסיסית (קצבה מהקופות + הכנסה נוספת)
        base_monthly = total_pension_monthly + other_inc_monthly
        effective_taxable_base = max(0, base_monthly - mon_exempt_val)
        
        # הכנסה כולל חלק המענק
        total_monthly_with_grant = effective_taxable_base + (ann_grant_part / 12)
        
        tax_total, m_rate = calculate_income_tax(total_monthly_with_grant, credit_pts_spread)
        tax_base, _ = calculate_income_tax(effective_taxable_base, credit_pts_spread)
        
        tax_on_grant_only = (tax_total - tax_base) * 12
        
        rows.append({
            "שנה": yr,
            "הכנסה שנתית קיימת": fmt_num(base_monthly * 12),
            "חלק מענק לפריסה": fmt_num(ann_grant_part),
            "סה\"כ הכנסה לדו\"ח": fmt_num((base_monthly * 12) + ann_grant_part),
            "מס שנתי על חלק המענק": fmt_num(tax_on_grant_only),
            "מדרגת מס שולית": f"{m_rate*100:.0f}%"
        })

    st.table(pd.DataFrame(rows))
    
    # סיכום כדאיות
    st.divider()
    st.subheader("4. בדיקת כדאיות כלכלית")
    total_tax_spread = sum([float(r["מס שנתי על חלק המענק"].replace('₪','').replace(',','')) for r in rows])
    tax_no_spread = taxable_grant * 0.47
    
    c1, c2, c3 = st.columns(3)
    c1.metric("חיסכון מס בפריסה", fmt_num(tax_no_spread - total_tax_spread))
    c2.metric("מס אפקטיבי על המענק", f"{(total_tax_spread / taxable_grant * 100):.1f}%")
    
    # גרף כדאיות (הון מול קצבה)
    saving_pension_15y = (calculate_income_tax(total_pension_monthly, credit_points)[0] - 
                          calculate_income_tax(max(0, total_pension_monthly - mon_exempt_val), credit_points)[0]) * 180
    
    fig = go.Figure(data=[
        go.Bar(name='הון פטור מידי', x=['כדאיות'], y=[rem_sal_base * (1 - pct_to_pension/100)], marker_color='#2ecc71'),
        go.Bar(name='חיסכון מס בקצבה (15 שנה)', x=['כדאיות'], y=[saving_pension_15y], marker_color='#3498db')
    ])
    st.plotly_chart(fig)

if __name__ == "__main__":
    main()
