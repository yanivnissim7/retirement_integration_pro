import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- נתוני יסוד 2026 ---
KITZBA_MAX = 9430 
STAGES = {
    2026: {"pct": 0.575},
    2027: {"pct": 0.625},
    2028: {"pct": 0.670}
}
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

    # אתחול session_state לשמירה על רציפות נתונים
    if 'v_pension' not in st.session_state: st.session_state.v_pension = 0.0
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]

    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח", value="")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 1, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0)
        st.divider()
        st.header("💰 מענקים (161)")
        total_grant_bruto = st.number_input("סך מענק ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע", value=13750)
        past_exempt_grants = st.number_input("פטורים בעבר", value=0)

    # חישובי 161 וקיזוז (נוסחת נסיגה)
    exempt_limit = min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT)
    total_exempt_grant = min(total_grant_bruto, seniority * exempt_limit)
    taxable_grant = total_grant_bruto - total_exempt_grant
    seniority_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_val = (total_exempt_grant + past_exempt_grants) * 1.35 * seniority_factor

    st.markdown(f"<h1>אפקט - תכנון פרישה אסטרטגי</h1>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "🔄 דוח פריסה", "📊 כדאיות ותחזית"])

    with tab1:
        st.subheader("ריכוז קצבאות וצבירות")
        st.session_state.v_pension = st.number_input("קצבה חודשית ותיקה/תקציבית ₪", value=float(st.session_state.v_pension))
        
        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        sum_honi = 0.0
        sum_kitzbati_cap = 0.0
        pension_from_funds = 0.0
        pension_for_spread_from_funds = 0.0

        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1, 1])
            fund['name'] = c1.text_input(f"קופה {i+1}", fund['name'], key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if fund['type']=="קצבתי" else 1, key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund['amount']), key=f"a_{i}")
            if fund['type'] == "קצבתי":
                sum_kitzbati_cap += fund['amount']
                fund['coeff'] = c4.number_input("מקדם", value=float(fund['coeff']), key=f"c_{i}")
                p_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                pension_from_funds += p_val
                fund['include'] = c5.checkbox("בפריסה?", value=fund['include'], key=f"inc_{i}")
                if fund['include']: pension_for_spread_from_funds += p_val
            else:
                sum_honi += fund['amount']

        # סך כל הקצבה העתידית (ותיקה + כל הקופות)
        total_monthly_pension_all = st.session_state.v_pension + pension_from_funds
        # סך הקצבה לחישובי פריסה (ותיקה + מה שסומן ב-V)
        total_monthly_pension_spread = st.session_state.v_pension + pension_for_spread_from_funds

        st.divider()
        r1, r2, r3 = st.columns(3)
        r1.metric("סה\"כ הון מזומן", fmt_num(sum_honi))
        r2.metric("צבירה לקצבה", fmt_num(sum_kitzbati_cap))
        r3.metric("קצבה חודשית ברוטו", fmt_num(total_monthly_pension_all))

    with tab2:
        st.subheader("קיבוע זכויות")
        sal_ptur_2026 = (KITZBA_MAX * STAGES[2026]["pct"]) * 180
        rem_sal_2026 = max(0, sal_ptur_2026 - reduction_val)
        
        pct_to_pension = st.select_slider("ניצול פטור לקצבה:", options=range(0,101,10), value=100)
        selected_mon_exemp = (rem_sal_2026 / 180) * (pct_to_pension / 100)
        rem_honi_ptur = rem_sal_2026 * (1 - (pct_to_pension / 100))
        
        st.metric("יתרת סל פטור (לאחר קיזוז)", fmt_num(rem_sal_2026))
        st.metric("פטור חודשי שנבחר", fmt_num(selected_mon_exemp))

    with tab3:
        st.subheader("דוח פריסה שנתי (כולל פנסיה ותיקה)")
        num_years = st.slider("שנות פריסה:", 1, 6, 6)
        work_inc = st.number_input("הכנסות עבודה נוספות (שנתי):", value=0)
        ann_tax_grant = taxable_grant / num_years
        
        rows = []
        total_tax_on_grant = 0
        for i in range(num_years):
            yr = ret_date.year + i
            yr_pct = STAGES.get(yr, STAGES[2028])["pct"]
            yr_mon_ex = (max(0, (KITZBA_MAX * yr_pct * 180) - reduction_val) / 180) * (pct_to_pension / 100)
            
            p_ann = total_monthly_pension_spread * 12
            total_ann_bruto = p_ann + (work_inc if i==0 else 0) + ann_tax_grant
            
            tax_total, m_r = calculate_income_tax(max(0, (total_ann_bruto/12) - yr_mon_ex), credit_points)
            tax_base, _ = calculate_income_tax(max(0, ((p_ann + (work_inc if i==0 else 0))/12) - yr_mon_ex), credit_points)
            tax_yr_grant = (tax_total - tax_base) * 12
            total_tax_on_grant += tax_yr_grant

            rows.append({
                "שנה": yr,
                "קצבה שנתית (ותיקה+קופות)": fmt_num(p_ann),
                "מענק בפריסה": fmt_num(ann_tax_grant),
                "סה\"כ ברוטו": fmt_num(total_ann_bruto),
                "מס על המענק": fmt_num(max(0, tax_yr_grant)),
                "מדרגה": f"{m_r*100:.0f}%"
            })
        st.table(pd.DataFrame(rows))
        st.success(f"חיסכון מס בפריסה: {fmt_num((taxable_grant * 0.47) - total_tax_on_grant)}")

    with tab4:
        st.subheader("כדאיות כלכלית ותחזית נטו")
        
        # חישוב חיסכון חודשי אמיתי
        forecast_list = []
        for yr in [2026, 2027, 2028]:
            yr_pct = STAGES[yr]["pct"]
            yr_mon_ex = (max(0, (KITZBA_MAX * yr_pct * 180) - reduction_val) / 180) * (pct_to_pension / 100)
            
            tax_no_ex, _ = calculate_income_tax(total_monthly_pension_all, credit_points)
            tax_with_ex, _ = calculate_income_tax(max(0, total_monthly_pension_all - yr_mon_ex), credit_points)
            forecast_list.append({"שנה": yr, "חיסכון": tax_no_ex - tax_with_ex})

        df_f = pd.DataFrame(forecast_list)
        total_15y = (df_f.iloc[0]['חיסכון']*12) + (df_f.iloc[1]['חיסכון']*12) + (df_f.iloc[2]['חיסכון']*156)

        c1, c2 = st.columns(2)
        c1.metric("הון פטור היום", fmt_num(rem_honi_ptur))
        c2.metric("חיסכון מס מצטבר (15 שנה)", fmt_num(total_15y))

        fig = go.Figure(data=[
            go.Bar(name='הון מזומן פטור', x=['השוואה'], y=[rem_honi_ptur], marker_color='#2ecc71', text=fmt_num(rem_honi_ptur), textposition='auto'),
            go.Bar(name='חיסכון מס (15 שנה)', x=['השוואה'], y=[total_15y], marker_color='#3498db', text=fmt_num(total_15y), textposition='auto')
        ])
        st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"📊 **תחזית נטו:** ב-2026 תחסוך **{fmt_num(df_f.iloc[0]['חיסכון'])}** במיסוי הקצבה בכל חודש. ב-2028 החיסכון יגדל ל-**{fmt_num(df_f.iloc[2]['חיסכון'])}**.")

if __name__ == "__main__":
    main()
