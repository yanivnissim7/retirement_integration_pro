import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- נתוני יסוד מעודכנים 2026 ---
KITZBA_MEZAKA_MAX = 9430 # תקרת קצבה מזכה (הערכה ל-2026)
PCT_PTUR_2026 = 0.575    # 57.5% פטור
MON_PTUR_VAL = KITZBA_MEZAKA_MAX * PCT_PTUR_2026 # 5,422 ש"ח
SAL_PTUR_MAX = MON_PTUR_VAL * 180 # 975,960 ש"ח (עיגול ל-976,000)

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
    st.set_page_config(page_title="אפקט - חישוב מדויק 2026", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח", value="")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 3, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק (משפיע על נוסחת הנסיגה)", value=35.0)
        
        st.divider()
        st.header("💰 מענקים (טופס 161)")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=500000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("מענקים פטורים ב-15 שנה אחרונות", value=0)

    # --- חישוב פטור על המענק (161) ---
    exempt_limit = min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT)
    total_exempt_grant = min(total_grant_bruto, seniority * exempt_limit)
    taxable_grant = total_grant_bruto - total_exempt_grant
    
    # --- תיקון נוסחת הנסיגה (הפגיעה בסל הפטור) ---
    # אם הוותק מעל 32, המקדם 1.35 מוכפל ביחס של 32/ותק
    seniority_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_value = (total_exempt_grant + past_exempt_grants) * 1.35 * seniority_factor
    
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction_value)

    st.markdown(f"<h1>תכנון פרישה אסטרטגי - אפקט</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "🔄 דוח פריסה", "📊 כדאיות כלכלית"])

    with tab1:
        st.subheader("ריכוז קצבאות וצבירות")
        v_pension = st.number_input("קצבה ותיקה/תקציבית חודשית:", value=0)
        
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'name': 'קופה 1', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]
        
        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        total_new_pension = 0.0
        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 1])
            fund['name'] = c1.text_input(f"קופה {i+1}", fund.get('name',''), key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund.get('amount',0)), key=f"a_{i}")
            if fund['type'] == 'קצבתי':
                fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
                fund['include'] = c5.checkbox("בפריסה?", value=fund.get('include', True), key=f"inc_{i}")
                if fund['include']:
                    total_new_pension += fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0

    with tab2:
        st.subheader("קיבוע זכויות - ניתוח סל הפטור (מדדי 2026)")
        st.write(f"סך סל הפטור ברוטו (2026): **{fmt_num(SAL_PTUR_MAX)}**")
        st.write(f"קיזוז בגין מענקים (לאחר מקדם ותק {seniority_factor:.2f}): **{fmt_num(reduction_value)}**")
        st.success(f"יתרת סל הפטור לניצול: **{fmt_num(rem_sal_base)}**")
        
        pct_to_pension = st.select_slider("חלוקת יתרת הסל:", options=range(0,101,10), value=0, help="0% = הכל למשיכה הונית")
        selected_mon_exemp = (rem_sal_base / 180) * (pct_to_pension / 100)
        rem_honi_ptur = rem_sal_base * (1 - (pct_to_pension / 100))
        
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("פטור חודשי לקצבה", fmt_num(selected_mon_exemp))
        c2.metric("הון פטור למשיכה", fmt_num(rem_honi_ptur))

    with tab3:
        st.subheader("דוח פריסה (חייב בפריסה: " + fmt_num(taxable_grant) + ")")
        num_years = st.slider("שנות פריסה:", 1, 6, 6)
        ann_tax_grant = taxable_grant / num_years
        
        rows = []
        for i in range(num_years):
            yr = ret_date.year + i
            ann_pension = (v_pension + total_new_pension) * 12
            total_bruto = ann_pension + ann_tax_grant
            tax_t, m_r = calculate_income_tax(max(0, (total_bruto/12) - selected_mon_exemp), credit_points)
            rows.append({
                "שנה": yr,
                "קצבה שנתית": fmt_num(ann_pension),
                "חלק מענק בפריסה": fmt_num(ann_tax_grant),
                "סה\"כ ברוטו שנתי": fmt_num(total_bruto),
                "מדרגת מס": f"{m_r*100:.0f}%"
            })
        st.table(pd.DataFrame(rows))

    with tab4:
        st.subheader("השוואת מקסימום: הון מול חיסכון מס")
        
        # חישוב חיסכון מס מקסימלי (100% לקצבה)
        all_pension = v_pension + total_new_pension
        tax_raw, _ = calculate_income_tax(all_pension, credit_points)
        tax_max_ex, _ = calculate_income_tax(max(0, all_pension - (rem_sal_base/180)), credit_points)
        max_saving_15y = (tax_raw - tax_max_ex) * 180

        fig = go.Figure(data=[
            go.Bar(name='מקסימום הון פטור', x=['פוטנציאל'], y=[rem_sal_base], marker_color='#2ecc71', text=fmt_num(rem_sal_base), textposition='auto'),
            go.Bar(name='מקסימום חיסכון (15 שנה)', x=['פוטנציאל'], y=[max_saving_15y], marker_color='#3498db', text=fmt_num(max_saving_15y), textposition='auto')
        ])
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
