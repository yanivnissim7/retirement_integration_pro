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
    st.set_page_config(page_title="אפקט - תכנון פרישה אסטרטגי", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח", value="")
        ret_date = st.date_input("תאריך פרישה", value=date(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=33.4)
        
        st.divider()
        st.header("💰 מענקים (טופס 161)")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=968000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("מענקים פטורים בעבר", value=0)

    # --- חישובי ליבה ---
    exempt_limit = min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT)
    total_exempt_grant = min(total_grant_bruto, seniority * exempt_limit)
    taxable_grant = total_grant_bruto - total_exempt_grant
    
    # נוסחת הנסיגה (1.35)
    reduction = ((total_exempt_grant + past_exempt_grants) * 1.35) * (32/seniority if seniority > 32 else 1)
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction)

    st.markdown(f"<h1>תכנון פרישה אסטרטגי - אפקט</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "🔄 דוח פריסה", "📊 כדאיות כלכלית"])

    with tab1:
        st.subheader("ריכוז צבירות ומקדמים")
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]

        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        total_pension_to_spread = 0.0
        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 1])
            fund['name'] = c1.text_input(f"קופה {i+1}", fund.get('name',''), key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund.get('amount',0)), key=f"a_{i}")
            if fund['type'] == 'קצבתי':
                fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
                fund['include'] = c5.checkbox("כלול בפריסה?", value=fund.get('include', True), key=f"inc_{i}")
                if fund['include']:
                    total_pension_to_spread += fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0

    with tab2:
        st.subheader("קיבוע זכויות - ניצול סל הפטור")
        pct_to_pension = st.select_slider("אחוז מהפטור לטובת הקצבה (היתרה להון):", options=range(0,101,10), value=0)
        selected_mon_exemp = (rem_sal_base / 180) * (pct_to_pension / 100)
        rem_honi_ptur = rem_sal_base * (1 - (pct_to_pension / 100))
        
        c_k1, c_k2 = st.columns(2)
        c_k1.metric("פטור חודשי על הקצבה", fmt_num(selected_mon_exemp))
        c_k2.metric("יתרת הון פטורה למשיכה", fmt_num(rem_honi_ptur))

    with tab3:
        st.subheader("דוח פריסת מס")
        st.info(f"**סיכום 161:** פטור: {fmt_num(total_exempt_grant)} | חייב לפריסה: {fmt_num(taxable_grant)}")
        
        is_after_oct = ret_date.month >= 10
        start_year = st.selectbox("שנת תחילת פריסה:", [ret_date.year, ret_date.year + 1])
        num_years = st.slider("שנות פריסה:", 1, 5 if (not is_after_oct and start_year > ret_date.year) else 6, 6)
        
        first_year_work = st.number_input("הכנסות עבודה שנה א' (ברוטו):", value=0)
        other_inc_monthly = st.number_input("הכנסה חודשית צפויה נוספת:", value=0)

        ann_taxable = taxable_grant / num_years
        spread_rows = []
        for i in range(num_years):
            yr = start_year + i
            base_annual = first_year_work if (i == 0 and yr == ret_date.year) else (total_pension_to_spread + other_inc_monthly) * 12
            total_annual = base_annual + ann_taxable
            tax_total, m_rate = calculate_income_tax(max(0, (total_annual/12) - selected_mon_exemp), credit_points)
            spread_rows.append({"שנה": yr, "ברוטו שנתי לדו\"ח": fmt_num(total_annual), "שולי": f"{m_rate*100:.0f}%"})
        st.table(pd.DataFrame(spread_rows))

    with tab4:
        st.subheader("בדיקת כדאיות: הון מזומן מול חיסכון במס")
        
        # חישוב חיסכון אמיתי: מס בלי פטור בכלל מול מס עם הפטור שנבחר
        tax_raw, _ = calculate_income_tax(total_pension_to_spread, credit_points)
        tax_after_exemp, _ = calculate_income_tax(max(0, total_pension_to_spread - selected_mon_exemp), credit_points)
        
        monthly_saving = tax_raw - tax_after_exemp
        total_saving_15y = monthly_saving * 180
        
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("מזומן פטור ביד (היום)", fmt_num(rem_honi_ptur))
        col_res2.metric("חיסכון מס מצטבר (15 שנה)", fmt_num(total_saving_15y))
        
        # גרף השוואה
        fig_bar = go.Figure(data=[
            go.Bar(name='הון מזומן פטור היום', x=['בחירה כלכלית'], y=[rem_honi_ptur], marker_color='#2ecc71', text=fmt_num(rem_honi_ptur), textposition='auto'),
            go.Bar(name='חיסכון מס מצטבר בקצבה', x=['בחירה כלכלית'], y=[total_saving_15y], marker_color='#3498db', text=fmt_num(total_saving_15y), textposition='auto')
        ])
        fig_bar.update_layout(barmode='group', height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.write(f"👉 **השורה התחתונה:** אם תבחר לנצל את הפטור לקצבה, תחסוך בכל חודש **{fmt_num(monthly_saving)}** בתשלומי מס הכנסה.")

    st.divider()
    st.markdown("<p style='text-align:center; color:gray; font-size:0.8em;'>אפקט סוכנות לביטוח - תכנון פרישה אסטרטגי | 2026</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
