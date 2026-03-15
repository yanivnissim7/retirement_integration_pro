import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- פרמטרים חוקיים ---
KITZBA_MAX = 9430 
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
    st.set_page_config(page_title="אפקט - מערכת מומחה לפרישה", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; } div.stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }</style>""", unsafe_allow_html=True)

    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]
    if 'v_pension' not in st.session_state: st.session_state.v_pension = 0.0

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("📋 פרטי הדוח")
        agent_name = st.text_input("שם הסוכן / המתכנן", value="שם הסוכן שלך")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        st.divider()
        st.header("👤 נתוני בסיס")
        ret_date = st.date_input("תאריך פרישה", value=date(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0, step=0.1)
        st.divider()
        st.header("💰 מענקים והכנסות")
        total_grant_bruto = st.number_input("סך מענקים ברוטו (161)", value=968000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("פטורים ב-15 שנה אחרונות", value=0)
        work_inc_ret_year = st.number_input("הכנסת עבודה בשנת הפרישה (ברוטו)", value=150000)

    # --- מנוע חישוב נסיגה ---
    actual_exempt_161 = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant = total_grant_bruto - actual_exempt_161
    s_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_val = (actual_exempt_161 + past_exempt_grants) * 1.35 * s_factor

    tab1, tab2, tab3, tab4 = st.tabs(["💰 קופות וצבירה", "📑 קיבוע זכויות ונטו", "🔄 דוח פריסה", "📊 כדאיות כלכלית"])

    # --- TAB 1 & 2 (נשארו דומים לחישובים הקודמים) ---
    with tab1:
        pension_total = st.session_state.v_pension
        pension_for_spread = st.session_state.v_pension
        for i, fund in enumerate(st.session_state.funds):
            p_val = fund['amount'] / fund['coeff'] if fund.get('type') == 'קצבתי' and fund['coeff'] > 0 else 0
            pension_total += p_val
            if fund.get('include', True): pension_for_spread += p_val
        st.metric("קצבה חודשית ברוטו חזויה", fmt_num(pension_total))

    with tab2:
        sal_26 = max(0, (KITZBA_MAX * 0.575 * 180) - reduction_val)
        sal_28 = max(0, (KITZBA_MAX * 0.670 * 180) - reduction_val)
        pct_to_pension = st.select_slider("אחוז ניצול פטור לקצבה", options=range(0,101,10), value=100)
        mon_ex_26 = (sal_26 / 180) * (pct_to_pension / 100)
        mon_ex_28 = (sal_28 / 180) * (pct_to_pension / 100)
        
        tax_no_ex, _ = calculate_income_tax(pension_total, credit_points)
        tax_with_ex_26, _ = calculate_income_tax(max(0, pension_total - mon_ex_26), credit_points)
        tax_with_ex_28, _ = calculate_income_tax(max(0, pension_total - mon_ex_28), credit_points)

    # --- TAB 3: דוח פריסה משופר ---
    with tab3:
        st.subheader("ניתוח פריסת מענקים (סעיף 8ג)")
        
        # לוגיקה של 1.10
        is_late_retirement = ret_date.month >= 10
        default_start_year = ret_date.year + 1 if is_late_retirement else ret_date.year
        
        c1, c2 = st.columns(2)
        start_spread_year = c1.number_input("שנת תחילת פריסה", value=default_start_year)
        spread_years = c2.selectbox("מספר שנות פריסה", [1, 2, 3, 4, 5, 6], index=5)
        
        ann_grant = taxable_grant / spread_years
        data_spread = []
        for i in range(spread_years):
            yr = start_spread_year + i
            # הכנסה מעבודה - רק בשנת הפרישה המקורית
            inc_work = work_inc_ret_year if yr == ret_date.year else 0
            # קצבה שנתית
            inc_pension = (pension_for_spread * 12)
            # סה"כ הכנסה שנתית כולל החלק הפרוס מהמענק
            total_annual_taxable = inc_work + inc_pension + ann_grant
            
            tax_full, _ = calculate_income_tax(total_annual_taxable/12, credit_points)
            tax_base, _ = calculate_income_tax((inc_work + inc_pension)/12, credit_points)
            tax_on_grant = (tax_full - tax_base) * 12
            
            data_spread.append([
                yr, 
                fmt_num(inc_work), 
                fmt_num(inc_pension), 
                fmt_num(ann_grant), 
                fmt_num(total_annual_taxable),
                fmt_num(max(0, tax_on_grant))
            ])
        
        df_spread = pd.DataFrame(data_spread, columns=["שנה", "הכנסה מעבודה", "קצבה שנתית", "מענק פרוס", "סה\"כ הכנסה למס", "מס שנתי משוער"])
        st.table(df_spread)

    # --- TAB 4: כדאיות כלכלית מורחבת ---
    with tab4:
        st.subheader("ניתוח כדאיות: 2026 מול 2028 ואימפקט מצטבר")
        
        net_26 = pension_total - tax_with_ex_26
        net_28 = pension_total - tax_with_ex_28
        diff_monthly = net_28 - net_26
        impact_15_years = (tax_no_ex - tax_with_ex_28) * 180 # תוספת הנטו המקסימלית לאורך 180 חודשים
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("קצבת נטו - 2026", fmt_num(net_26), help=f"ברוטו: {fmt_num(pension_total)}")
        with col2:
            st.metric("קצבת נטו - 2028", fmt_num(net_28), f"{fmt_num(diff_monthly)} תוספת")
        with col3:
            st.metric("חיסכון מס מצטבר (15 שנה)", fmt_num(impact_15_years))
            
        st.divider()
        
        # טבלת השוואה ברוטו/נטו
        comparison_data = {
            "פרמטר": ["קצבת ברוטו", "פטור חודשי ממס", "מס הכנסה חודשי", "קצבת נטו"],
            "מצב 2026": [fmt_num(pension_total), fmt_num(mon_ex_26), fmt_num(tax_with_ex_26), fmt_num(net_26)],
            "מצב 2028": [fmt_num(pension_total), fmt_num(mon_ex_28), fmt_num(tax_with_ex_28), fmt_num(net_28)]
        }
        st.table(pd.DataFrame(comparison_data))
        
        # גרף אימפקט
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[i for i in range(1, 16)], 
                                 y=[(tax_no_ex - tax_with_ex_28) * 12 * i for i in range(1, 16)],
                                 mode='lines+markers', name='חיסכון מס מצטבר'))
        fig.update_layout(title="צבירת חיסכון המס לאורך 15 שנות פרישה", xaxis_title="שנים מרגע קיבוע", yaxis_title="₪ מצטבר")
        st.plotly_chart(fig)

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray;'>מערכת אפקט | כלי עזר לתכנון פרישה אופטימלי</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
