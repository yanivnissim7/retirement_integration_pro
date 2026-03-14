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
    st.markdown("""<style>.main { direction: rtl; text-align: right; } div[data-testid="stMetricValue"] { color: #1f77b4; }</style>""", unsafe_allow_html=True)

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

    # --- חישובי ליבה: פטור וחייב ---
    exempt_limit = min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT)
    total_exempt_grant = min(total_grant_bruto, seniority * exempt_limit)
    taxable_grant = total_grant_bruto - total_exempt_grant
    
    # נוסחת הנסיגה (1.35) לקיבוע זכויות
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
        c_k2.metric("הון פטור שנותר (אחרי קיזוז)", fmt_num(rem_honi_ptur))

    with tab3:
        st.subheader("דוח פריסת מס מפורט")
        # הצגת נתוני פטור/חייב שביקשת
        st.info(f"**סיכום 161:** מענק פטור: {fmt_num(total_exempt_grant)} | מענק חייב לפריסה: {fmt_num(taxable_grant)}")
        
        is_after_oct = ret_date.month >= 10
        start_year = st.selectbox("שנת תחילת פריסה:", [ret_date.year, ret_date.year + 1])
        
        num_years = st.slider("מספר שנות פריסה:", 1, 5 if (not is_after_oct and start_year > ret_date.year) else 6, 6)
        
        first_year_work = st.number_input("הכנסות עבודה בשנה הראשונה (ברוטו שנתי):", value=0)
        other_inc_monthly = st.number_input("הכנסה חודשית נוספת צפויה (שכר/פנסיה):", value=0)

        ann_taxable = taxable_grant / num_years
        spread_rows = []
        total_tax_spread = 0
        
        for i in range(num_years):
            yr = start_year + i
            base_annual = first_year_work if (i == 0 and yr == ret_date.year) else (total_pension_to_spread + other_inc_monthly) * 12
            total_annual = base_annual + ann_taxable
            
            tax_total, m_rate = calculate_income_tax(max(0, (total_annual/12) - selected_mon_exemp), credit_points)
            tax_base, _ = calculate_income_tax(max(0, (base_annual/12) - selected_mon_exemp), credit_points)[0], 0
            tax_on_grant = (tax_total - tax_base) * 12
            total_tax_spread += max(0, tax_on_grant)

            spread_rows.append({
                "שנה": yr, "הכנסה בסיסית": fmt_num(base_annual), "מענק חייב": fmt_num(ann_taxable),
                "ברוטו שנתי לדו\"ח": fmt_num(total_annual), "מס על המענק": fmt_num(max(0, tax_on_grant)), "שולי": f"{m_rate*100:.0f}%"
            })
        st.table(pd.DataFrame(spread_rows))
        
        tax_no_spread = taxable_grant * 0.47
        st.success(f"חיסכון במיסוי בזכות הפריסה: {fmt_num(tax_no_spread - total_tax_spread)}")

    with tab4:
        st.subheader("ניתוח כדאיות: הון פטור מול קצבה פטורה")
        
        # חישוב חיסכון מס בקצבה ל-15 שנה
        tax_no_ex, _ = calculate_income_tax(total_pension_to_spread, credit_points)
        tax_with_ex, _ = calculate_income_tax(max(0, total_pension_to_spread - (rem_sal_base/180)), credit_points)
        total_pension_saving_15y = (tax_no_ex - tax_with_ex) * 180
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # גרף עוגה - חלוקת סל הפטור
            fig_pie = go.Figure(data=[go.Pie(labels=['הון פטור', 'פטור לקצבה'], 
                                           values=[rem_honi_ptur, (rem_sal_base * (pct_to_pension/100))],
                                           hole=.3, marker_colors=['#2ecc71', '#3498db'])])
            fig_pie.update_layout(title_text="חלוקת ניצול סל הפטור")
            st.plotly_chart(fig_pie)

        with col_g2:
            # גרף עמודות - כדאיות כלכלית
            fig_bar = go.Figure(data=[
                go.Bar(name='הון מזומן פטור היום', x=['השוואה כלכלית'], y=[rem_honi_ptur], marker_color='#2ecc71', text=fmt_num(rem_honi_ptur), textposition='auto'),
                go.Bar(name='חיסכון מס מצטבר בקצבה', x=['השוואה כלכלית'], y=[total_pension_saving_15y * (pct_to_pension/100)], marker_color='#3498db', text=fmt_num(total_pension_saving_15y * (pct_to_pension/100)), textposition='auto')
            ])
            fig_bar.update_layout(title_text="מה תקבל נטו בכיס? (הון מול חיסכון במס)")
            st.plotly_chart(fig_bar)
            
        st.write(f"**הסבר:** הגרף משווה בין לקיחת הכסף כהון פטור עכשיו (₪{fmt_num(rem_honi_ptur)}) לבין החיסכון המצטבר בתשלומי מס הכנסה על הפנסיה לאורך 15 שנה.")

    st.divider()
    st.markdown("""<div style="font-size: 0.8em; color: gray; text-align: center;"><b>דיסקליימר:</b> סימולציה זו מבוססת על נתוני הלקוח ואינה מהווה ייעוץ מס רשמי. מומלץ לבחון את הנתונים מול פקיד שומה.</div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
