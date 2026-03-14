import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- נתוני יסוד 2026 ---
KITZBA_MAX = 9430 
STAGES = {2026: 0.575, 2027: 0.625, 2028: 0.670}
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
    st.set_page_config(page_title="אפקט - ניהול פרישה מלא", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    # --- אתחול נתונים ב-Session ---
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]
    if 'v_pension' not in st.session_state: st.session_state.v_pension = 0.0

    # --- Sidebar ---
    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 1, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק (משפיע על הנסיגה)", value=35.0, step=0.1)
        
        st.divider()
        st.header("💰 מענקים (161)")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("מענקים פטורים ב-15 שנה", value=0)

    # --- חישובי ותק ונוסחת נסיגה ---
    actual_exempt_161 = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant = total_grant_bruto - actual_exempt_161
    
    # נוסחת הנסיגה המתוקנת לוותק מעל 32
    s_factor = 32 / seniority if seniority > 32 else 1.0
    eff_multiplier = 1.35 * s_factor
    reduction_val = (actual_exempt_161 + past_exempt_grants) * eff_multiplier

    st.markdown(f"<h1>אפקט - תכנון פרישה אסטרטגי</h1>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "🔄 דוח פריסה", "📊 כדאיות 2026/28"])

    # --- טאב 1: ריכוז קופות (החזרת המנגנון) ---
    with tab1:
        st.subheader("ניהול קופות וצבירות")
        st.session_state.v_pension = st.number_input("קצבה חודשית ותיקה/תקציבית ₪", value=float(st.session_state.v_pension))
        
        if st.button("➕ הוסף קופה חדשה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        sum_honi = 0.0
        sum_kitzbati_cap = 0.0
        pension_from_funds_total = 0.0
        pension_for_spread_only = st.session_state.v_pension

        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1, 1])
            fund['name'] = c1.text_input(f"שם קופה {i+1}", fund['name'], key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if fund['type']=="קצבתי" else 1, key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund['amount']), key=f"a_{i}")
            
            if fund['type'] == "קצבתי":
                sum_kitzbati_cap += fund['amount']
                fund['coeff'] = c4.number_input("מקדם", value=float(fund['coeff']), key=f"c_{i}")
                p_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                pension_from_funds_total += p_val
                fund['include'] = c5.checkbox("בפריסה?", value=fund['include'], key=f"inc_{i}")
                if fund['include']: pension_for_spread_only += p_val
            else:
                sum_honi += fund['amount']

        total_pension_all = st.session_state.v_pension + pension_from_funds_total
        
        st.divider()
        res_c1, res_c2, res_c3 = st.columns(3)
        res_c1.metric("סה\"כ הון (מזומן)", fmt_num(sum_honi))
        res_c2.metric("צבירה לקצבה", fmt_num(sum_kitzbati_cap))
        res_c3.metric("קצבה חודשית ברוטו", fmt_num(total_pension_all))

    # --- טאב 2: קיבוע זכויות ---
    with tab2:
        st.subheader("ניתוח סל הפטור (מדדי 2026)")
        sal_ptur_26 = (KITZBA_MAX * 0.575) * 180
        rem_sal_26 = max(0, sal_ptur_26 - reduction_val)
        
        pct_to_pension = st.select_slider("חלוקת הפטור לקצבה:", options=range(0,101,10), value=100)
        mon_ex_26 = (rem_sal_26 / 180) * (pct_to_pension / 100)
        
        tax_val, _ = calculate_income_tax(max(0, total_pension_all - mon_ex_26), credit_points)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("יתרת הון פטורה", fmt_num(rem_sal_26))
        col2.metric("פטור חודשי", fmt_num(mon_ex_26))
        col3.metric("קצבה נטו בכיס", fmt_num(total_pension_all - tax_val))

    # --- טאב 3: דוח פריסה ---
    with tab3:
        st.subheader("דוח פריסה שנתי")
        num_years = st.slider("שנות פריסה:", 1, 6, 6)
        ann_tax_grant = taxable_grant / num_years
        
        rows = []
        for i in range(num_years):
            yr = ret_date.year + i
            # עדכון פטור דינמי לשנים הבאות
            yr_pct = 0.575 if yr < 2027 else (0.625 if yr == 2027 else 0.670)
            yr_mon_ex = (max(0, (KITZBA_MAX * yr_pct * 180) - reduction_val) / 180) * (pct_to_pension / 100)
            
            p_ann = pension_for_spread_only * 12
            total_bruto = p_ann + ann_tax_grant
            tax_t, m_r = calculate_income_tax(max(0, (total_bruto/12) - yr_mon_ex), credit_points)
            
            rows.append({"שנה": yr, "קצבה (ותיקה+מסומנות)": fmt_num(p_ann), "מענק פריסה": fmt_num(ann_tax_grant), "סה\"כ ברוטו": fmt_num(total_bruto), "מדרגה": f"{m_r*100:.0f}%"})
        st.table(pd.DataFrame(rows))

    # --- טאב 4: כדאיות ---
    with tab4:
        st.subheader("📊 השוואת כדאיות אסטרטגית")
        
        # חישוב 15 שנה
        tax_no, _ = calculate_income_tax(total_pension_all, credit_points)
        
        # 2026
        save_26 = (tax_no - calculate_income_tax(max(0, total_pension_all - (rem_sal_26/180)), credit_points)[0]) * 180
        # 2028
        rem_sal_28 = max(0, (KITZBA_MAX * 0.670 * 180) - reduction_val)
        save_28 = (tax_no - calculate_income_tax(max(0, total_pension_all - (rem_sal_28/180)), credit_points)[0]) * 180

        c_a, c_b = st.columns(2)
        with c_a:
            st.markdown("#### מצב נוכחי 2026")
            fig1 = go.Figure(data=[
                go.Bar(name='הון פטור', x=['2026'], y=[rem_sal_26], marker_color='#2ecc71', text=fmt_num(rem_sal_26), textposition='auto'),
                go.Bar(name='חיסכון 15 שנה', x=['2026'], y=[save_26], marker_color='#3498db', text=fmt_num(save_26), textposition='auto')
            ])
            st.plotly_chart(fig1, use_container_width=True)
        with c_b:
            st.markdown("#### יעד סופי 2028")
            fig2 = go.Figure(data=[
                go.Bar(name='הון פטור', x=['2028'], y=[rem_sal_28], marker_color='#27ae60', text=fmt_num(rem_sal_28), textposition='auto'),
                go.Bar(name='חיסכון 15 שנה', x=['2028'], y=[save_28], marker_color='#2980b9', text=fmt_num(save_28), textposition='auto')
            ])
            st.plotly_chart(fig2, use_container_width=True)

if __name__ == "__main__":
    main()
