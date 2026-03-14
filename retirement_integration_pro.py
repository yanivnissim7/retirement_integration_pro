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
    st.set_page_config(page_title="אפקט - תכנון פרישה כולל ותיקות ותקציביות", layout="wide")
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
    reduction = ((total_exempt_grant + past_exempt_grants) * 1.35) * (32/seniority if seniority > 32 else 1)
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction)

    st.markdown(f"<h1>תכנון פרישה אסטרטגי - אפקט</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "🔄 דוח פריסה", "📊 כדאיות כלכלית"])

    with tab1:
        st.subheader("ריכוז קצבאות וצבירות")
        
        # שורה חדשה: פנסיה ותיקה / תקציבית
        st.markdown("##### 🏛️ פנסיה ותיקה / תקציבית / קצבה קיימת")
        col_v1, col_v2 = st.columns([3, 2])
        v_pension_name = col_v1.text_input("מקור הקצבה (ותיקה/תקציבית/אחר)", value="פנסיה ותיקה")
        v_pension_amount = col_v2.number_input("סכום קצבה חודשי ברוטו ₪", value=0.0)
        
        st.divider()
        st.markdown("##### 💳 קופות גמל וביטוחי מנהלים (צבירות)")
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]

        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        total_new_pension_to_spread = 0.0
        all_future_pension_total = v_pension_amount # מתחילים מהותיקה/תקציבית
        
        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 1])
            fund['name'] = c1.text_input(f"קופה {i+1}", fund.get('name',''), key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund.get('amount',0)), key=f"a_{i}")
            if fund['type'] == 'קצבתי':
                fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
                fund['include'] = c5.checkbox("כלול בפריסה?", value=fund.get('include', True), key=f"inc_{i}")
                pension_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                all_future_pension_total += pension_val
                if fund['include']:
                    total_new_pension_to_spread += pension_val

    with tab2:
        st.subheader("קיבוע זכויות")
        pct_to_pension = st.select_slider("ניצול פטור לקצבה:", options=range(0,101,10), value=0)
        selected_mon_exemp = (rem_sal_base / 180) * (pct_to_pension / 100)
        rem_honi_ptur = rem_sal_base * (1 - (pct_to_pension / 100))
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("פטור חודשי על הקצבה", fmt_num(selected_mon_exemp))
        col_m2.metric("יתרת הון פטורה", fmt_num(rem_honi_ptur))

    with tab3:
        st.subheader("דוח פריסת מס")
        st.info(f"מענק חייב לפריסה: {fmt_num(taxable_grant)}")
        
        is_after_oct = ret_date.month >= 10
        start_year = st.selectbox("שנת תחילת פריסה:", [ret_date.year, ret_date.year + 1])
        num_years = st.slider("שנות פריסה:", 1, 5 if (not is_after_oct and start_year > ret_date.year) else 6, 6)
        
        first_year_work = st.number_input("הכנסות עבודה שנה א' (משכורות ברוטו):", value=0)
        other_inc = st.number_input("הכנסה חודשית נוספת (שכר עתידי):", value=0)

        ann_tax = taxable_grant / num_years
        rows = []
        for i in range(num_years):
            yr = start_year + i
            # הכנסה בסיסית כוללת את הותיקה/תקציבית תמיד + הקופות החדשות שסומנו + שכר
            pension_base = v_pension_amount + total_new_pension_to_spread
            base_annual = first_year_work if (i == 0 and yr == ret_date.year) else (pension_base + other_inc) * 12
            total_annual = base_annual + ann_tax
            
            tax_t, m_r = calculate_income_tax(max(0, (total_annual/12) - selected_mon_exemp), credit_points)
            rows.append({"שנה": yr, "ברוטו שנתי כולל": fmt_num(total_annual), "שולי": f"{m_r*100:.0f}%"})
        st.table(pd.DataFrame(rows))

    with tab4:
        st.subheader("ניתוח כדאיות כלכלית")
        
        # חישוב חיסכון מבוסס על סך כל הקצבאות (כולל ותיקה)
        tax_no_exemp, _ = calculate_income_tax(all_future_pension_total, credit_points)
        tax_with_selected_exemp, _ = calculate_income_tax(max(0, all_future_pension_total - selected_mon_exemp), credit_points)
        
        monthly_saving = tax_no_exemp - tax_with_selected_exemp
        total_15y_saving = monthly_saving * 180

        c_r1, c_r2 = st.columns(2)
        c_r1.metric("הון פטור היום", fmt_num(rem_honi_ptur))
        c_r2.metric("חיסכון מס ב-15 שנה", fmt_num(total_15y_saving))

        fig = go.Figure(data=[
            go.Bar(name='הון מזומן פטור', x=['בחירה'], y=[rem_honi_ptur], marker_color='#2ecc71', text=fmt_num(rem_honi_ptur), textposition='auto'),
            go.Bar(name='חיסכון מס מצטבר', x=['בחירה'], y=[total_15y_saving], marker_color='#3498db', text=fmt_num(total_15y_saving), textposition='auto')
        ])
        st.plotly_chart(fig, use_container_width=True)
        st.write(f"החיסכון החודשי הצפוי בנטו שלך: **{fmt_num(monthly_saving)}**")

    st.divider()
    st.markdown("<p style='text-align:center; font-size:0.8em; color:gray;'>אפקט סוכנות לביטוח - תכנון פרישה אסטרטגי</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
