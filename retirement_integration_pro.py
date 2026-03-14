import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- נתוני יסוד ---
KITZBA_MAX = 9430 
STAGES = {
    2026: {"pct": 0.575, "label": "מצב נוכחי (2026)"},
    2028: {"pct": 0.670, "label": "מצב יעד (2028)"}
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
    st.set_page_config(page_title="אפקט - השוואת דורות פרישה", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    if 'v_pension' not in st.session_state: st.session_state.v_pension = 0.0
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]

    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 1, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0)
        st.divider()
        st.header("💰 מענקים (161)")
        total_grant_bruto = st.number_input("סך מענק ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע", value=13750)
        past_exempt_grants = st.number_input("פטורים בעבר", value=0)

    # חישוב 161 וקיזוז
    exempt_limit = min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT)
    total_exempt_grant = min(total_grant_bruto, seniority * exempt_limit)
    taxable_grant = total_grant_bruto - total_exempt_grant
    seniority_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_val = (total_exempt_grant + past_exempt_grants) * 1.35 * seniority_factor

    st.markdown(f"<h1>תכנון פרישה אסטרטגי - אפקט</h1>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות ונטו", "🔄 דוח פריסה", "📊 כדאיות 2026 vs 2028"])

    with tab1:
        st.subheader("ריכוז קצבאות וצבירות")
        st.session_state.v_pension = st.number_input("קצבה חודשית ותיקה/תקציבית ₪", value=float(st.session_state.v_pension))
        
        sum_honi = 0.0
        pension_from_funds = 0.0
        pension_for_spread = st.session_state.v_pension

        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1, 1])
            fund['name'] = c1.text_input(f"קופה {i+1}", fund['name'], key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if fund['type']=="קצבתי" else 1, key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund['amount']), key=f"a_{i}")
            if fund['type'] == "קצבתי":
                fund['coeff'] = c4.number_input("מקדם", value=float(fund['coeff']), key=f"c_{i}")
                p_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                pension_from_funds += p_val
                fund['include'] = c5.checkbox("בפריסה?", value=fund['include'], key=f"inc_{i}")
                if fund['include']: pension_for_spread += p_val
            else:
                sum_honi += fund['amount']

        total_pension_all = st.session_state.v_pension + pension_from_funds
        st.divider()
        st.metric("סה\"כ קצבה חודשית ברוטו (כולל הכל)", fmt_num(total_pension_all))

    with tab2:
        st.subheader("קיבוע זכויות וניתוח נטו")
        pct_to_pension = st.select_slider("חלוקת הפטור (0=הכל הון, 100=הכל קצבה):", options=range(0,101,10), value=100)
        
        # חישוב ל-2026
        sal_ptur_26 = (KITZBA_MAX * 0.575) * 180
        rem_sal_26 = max(0, sal_ptur_26 - reduction_val)
        mon_ex_26 = (rem_sal_26 / 180) * (pct_to_pension / 100)
        
        tax_val, _ = calculate_income_tax(max(0, total_pension_all - mon_ex_26), credit_points)
        netto = total_pension_all - tax_val

        col1, col2, col3 = st.columns(3)
        col1.metric("יתרת סל פטור (הון)", fmt_num(rem_sal_26))
        col2.metric("פטור חודשי ממס", fmt_num(mon_ex_26))
        col3.metric("קצבת נטו בכיס", fmt_num(netto))
        
        st.info(f"מתוך קצבת הברוטו של {fmt_num(total_pension_all)}, אתה משלם מס של {fmt_num(tax_val)} בלבד.")

    with tab3:
        st.subheader("דוח פריסה (השפעת ותיקה/תקציבית)")
        num_years = st.slider("שנות פריסה:", 1, 6, 6)
        ann_tax_grant = taxable_grant / num_years
        
        rows = []
        for i in range(num_years):
            yr = ret_date.year + i
            # עדכון פטור לפי השנה בפריסה
            yr_pct = 0.575 if yr < 2027 else (0.625 if yr == 2027 else 0.670)
            yr_mon_ex = (max(0, (KITZBA_MAX * yr_pct * 180) - reduction_val) / 180) * (pct_to_pension / 100)
            
            p_ann = pension_for_spread * 12
            total_ann = p_ann + ann_tax_grant
            tax_t, m_r = calculate_income_tax(max(0, (total_ann/12) - yr_mon_ex), credit_points)
            
            rows.append({"שנה": yr, "קצבה (ותיקה+מסומנות)": fmt_num(p_ann), "מענק פריסה": fmt_num(ann_tax_grant), "ברוטו שנתי": fmt_num(total_ann), "מדרגה": f"{m_r*100:.0f}%"})
        st.table(pd.DataFrame(rows))

    with tab4:
        st.subheader("📊 השוואת כדאיות: המצב היום (2026) מול היעד (2028)")
        
        results = {}
        for yr in [2026, 2028]:
            yr_pct = STAGES[yr]["pct"]
            total_sal_ptur = (KITZBA_MAX * yr_pct) * 180
            yr_rem_sal = max(0, total_sal_ptur - reduction_val)
            
            # הון פטור (אם בוחרים 0% לקצבה)
            honi_max = yr_rem_sal 
            # חיסכון במס 15 שנה (אם בוחרים 100% לקצבה)
            mon_ex = yr_rem_sal / 180
            tax_no, _ = calculate_income_tax(total_pension_all, credit_points)
            tax_yes, _ = calculate_income_tax(max(0, total_pension_all - mon_ex), credit_points)
            saving_15y = (tax_no - tax_yes) * 180
            results[yr] = {"honi": honi_max, "saving": saving_15y}

        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### 📍 מצב נוכחי (2026)")
            fig1 = go.Figure(data=[
                go.Bar(name='הון פטור 2026', x=['2026'], y=[results[2026]["honi"]], marker_color='#2ecc71', text=fmt_num(results[2026]["honi"]), textposition='auto'),
                go.Bar(name='חיסכון מס 15 שנה', x=['2026'], y=[results[2026]["saving"]], marker_color='#3498db', text=fmt_num(results[2026]["saving"]), textposition='auto')
            ])
            st.plotly_chart(fig1, use_container_width=True)

        with c2:
            st.markdown("#### 🚀 פוטנציאל עתידי (2028)")
            fig2 = go.Figure(data=[
                go.Bar(name='הון פטור 2028', x=['2028'], y=[results[2028]["honi"]], marker_color='#27ae60', text=fmt_num(results[2028]["honi"]), textposition='auto'),
                go.Bar(name='חיסכון מס 15 שנה', x=['2028'], y=[results[2028]["saving"]], marker_color='#2980b9', text=fmt_num(results[2028]["saving"]), textposition='auto')
            ])
            st.plotly_chart(fig2, use_container_width=True)
            
        st.success(f"שים לב: בשנת 2028, סל הפטור שלך גדל ב-**{fmt_num(results[2028]['honi'] - results[2026]['honi'])}** נוספים!")

if __name__ == "__main__":
    main()
