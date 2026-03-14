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
    st.set_page_config(page_title="אפקט - דוח פריסה וכדאיות", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)

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
    reduction = ((total_exempt_grant + past_exempt_grants) * 1.35) * (32/seniority if seniority > 32 else 1)
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction)

    st.markdown(f"<h1>תכנון פרישה אסטרטגי - אפקט</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "🔄 דוח פריסה", "📊 כדאיות כלכלית"])

    with tab1:
        st.subheader("ריכוז קצבאות וצבירות")
        v_pension_amount = st.number_input("קצבה חודשית קיימת (ותיקה/תקציבית) ברוטו ₪", value=0.0)
        
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'name': 'קופה 1', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]

        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        total_new_pension_to_spread = 0.0
        all_future_pension_total = v_pension_amount
        
        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 1])
            fund['name'] = c1.text_input(f"קופה {i+1}", fund.get('name',''), key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund.get('amount',0)), key=f"a_{i}")
            if fund['type'] == 'קצבתי':
                fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
                fund['include'] = c5.checkbox("כלול בפריסה?", value=fund.get('include', True), key=f"inc_{i}")
                p_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                all_future_pension_total += p_val
                if fund['include']:
                    total_new_pension_to_spread += p_val

    with tab2:
        st.subheader("קיבוע זכויות")
        pct_to_pension = st.select_slider("ניצול פטור לקצבה:", options=range(0,101,10), value=0)
        selected_mon_exemp = (rem_sal_base / 180) * (pct_to_pension / 100)
        rem_honi_ptur = rem_sal_base * (1 - (pct_to_pension / 100))
        st.metric("פטור חודשי שנבחר", fmt_num(selected_mon_exemp))
        st.metric("יתרת הון פטורה", fmt_num(rem_honi_ptur))

    with tab3:
        st.subheader("דוח פריסה שנתי (למס הכנסה)")
        st.info(f"מענק פטור: {fmt_num(total_exempt_grant)} | מענק חייב בפריסה: {fmt_num(taxable_grant)}")
        
        start_year = st.selectbox("שנת תחילת פריסה:", [ret_date.year, ret_date.year + 1])
        num_years = st.slider("שנות פריסה:", 1, 6, 6)
        other_inc_monthly = st.number_input("הכנסה חודשית נוספת בפריסה (שכר):", value=0)

        ann_tax_grant = taxable_grant / num_years
        spread_rows = []
        total_tax_spread = 0
        
        for i in range(num_years):
            yr = start_year + i
            # עמודה 1: קצבה שנתית (כולל הכל)
            annual_pension = (v_pension_amount + total_new_pension_to_spread + other_inc_monthly) * 12
            # עמודה 2: המענק
            # עמודה 3: ברוטו כולל
            total_annual_bruto = annual_pension + ann_tax_grant
            
            tax_total, m_r = calculate_income_tax(max(0, (total_annual_bruto/12) - selected_mon_exemp), credit_points)
            tax_base, _ = calculate_income_tax(max(0, (annual_pension/12) - selected_mon_exemp), credit_points)
            tax_on_grant = (tax_total - tax_base) * 12
            total_tax_spread += tax_on_grant

            spread_rows.append({
                "שנה": yr,
                "קצבה שנתית (X12)": fmt_num(annual_pension),
                "חלק מענק בפריסה": fmt_num(ann_tax_grant),
                "סה\"כ ברוטו שנתי": fmt_num(total_annual_bruto),
                "מס שנתי על המענק": fmt_num(max(0, tax_on_grant)),
                "מדרגת מס": f"{m_r*100:.0f}%"
            })
        
        st.table(pd.DataFrame(spread_rows))
        
        tax_no_spread = taxable_grant * 0.47
        st.markdown(f"**💰 חיסכון במס בזכות הפריסה:** <span style='color:green; font-size:1.2em;'>{fmt_num(tax_no_spread - total_tax_spread)}</span>", unsafe_allow_html=True)

    with tab4:
        st.subheader("השוואת מקסימום: הון מול חיסכון בקצבה")
        
        # חישוב מקסימום חיסכון (100% לקצבה)
        max_mon_exemp = rem_sal_base / 180
        t_raw, _ = calculate_income_tax(all_future_pension_total, credit_points)
        t_max_ex, _ = calculate_income_tax(max(0, all_future_pension_total - max_mon_exemp), credit_points)
        max_total_15y_saving = (t_raw - t_max_ex) * 180
        
        # חישוב נוכחי לפי הסליידר
        current_saving_15y = (t_raw - calculate_income_tax(max(0, all_future_pension_total - selected_mon_exemp), credit_points)[0]) * 180

        fig = go.Figure(data=[
            go.Bar(name='מקסימום הון פטור אפשרי', x=['השוואת פוטנציאל'], y=[rem_sal_base], marker_color='#2ecc71', text=fmt_num(rem_sal_base), textposition='auto'),
            go.Bar(name='מקסימום חיסכון במס (15 שנה)', x=['השוואת פוטנציאל'], y=[max_total_15y_saving], marker_color='#3498db', text=fmt_num(max_total_15y_saving), textposition='auto')
        ])
        
        fig.add_trace(go.Scatter(x=['השוואת פוטנציאל'], y=[current_saving_15y], name='חיסכון נוכחי (לפי בחירה)', mode='markers+text', text=[f"נוכחי: {fmt_num(current_saving_15y)}"], textposition="top center", marker=dict(color='red', size=12)))

        st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"**ניתוח כדאיות:** המקסימום שניתן לקבל במזומן היום הוא **{fmt_num(rem_sal_base)}**. מנגד, אם תבחר לנצל את מלוא הפטור לקצבה, שווי ההטבה המצטברת שלך ב-15 השנים הבאות עומד על **{fmt_num(max_total_15y_saving)}**.")

    st.divider()
    st.markdown("<p style='text-align:center; color:gray; font-size:0.8em;'>אפקט סוכנות לביטוח - דיסקליימר: סימולציה בלבד לצרכי המחשה.</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
