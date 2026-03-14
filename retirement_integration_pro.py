import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- נתוני יסוד 2026 ---
SAL_PTUR_MAX = 976005 
MAX_WAGE_FOR_EXEMPT = 13750 

def fmt_num(num): return f"{float(num):,.0f}"

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
    st.set_page_config(page_title="דוח פרישה אסטרטגי - אפקט", layout="wide")

    # CSS ליישור לימין (RTL)
    st.markdown("""
        <style>
        .main, .stTabs, div[data-testid="stMetricValue"], .stMarkdown, p, h1, h2, h3, label {
            direction: rtl;
            text-align: right !important;
        }
        .stTable { direction: rtl; }
        @media print {
            .stTabs [data-baseweb="tab-list"] { display: none; }
            .stButton, .stSlider, .stSelectbox, [data-testid="stSidebar"], header { display: none !important; }
            .main { width: 100% !important; direction: rtl; }
        }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 פרטי לקוח וסוכן")
        agent_name = st.text_input("שם הסוכן המטפל", value="ישראל ישראלי")
        client_name = st.text_input("שם הלקוח", value="")
        retirement_date = st.date_input("תאריך פרישה", value=date(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=33.4)
        
        st.divider()
        st.header("💰 מענקים")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=968000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("סך מענקים פטורים בעבר", value=0)

    st.markdown(f"<h1>דוח תכנון פרישה - אפקט סוכנות לביטוח</h1>", unsafe_allow_html=True)

    # --- 1. ריכוז קופות ---
    st.subheader("1. ריכוז קופות וצבירות")
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10}]

    if st.button("➕ הוסף קופה"):
        st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0})
        st.rerun()

    total_pension_from_funds = 0.0
    for i, fund in enumerate(st.session_state.funds):
        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
        fund['name'] = c1.text_input(f"קופה {i+1}", fund.get('name',''), key=f"n_{i}")
        fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if fund.get('type')=='קצבתי' else 1, key=f"t_{i}")
        fund['amount'] = c3.number_input("צבירה", value=float(fund.get('amount',0)), key=f"a_{i}")
        if fund['type'] == 'קצבתי':
            fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
            total_pension_from_funds += fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0

    st.divider()

    # --- 2. אופטימיזציה של סל הפטור ---
    actual_exempt_now = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant_for_spread = total_grant_bruto - actual_exempt_now
    seniority_ratio = 32 / seniority if seniority > 32 else 1
    reduction = ((actual_exempt_now + past_exempt_grants) * 1.35) * seniority_ratio
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction)
    max_mon_exemp = rem_sal_base / 180

    st.subheader("2. אופטימיזציה של סל הפטור")
    pct_to_pension = st.select_slider("אחוז מהפטור לטובת הקצבה:", options=range(0, 101, 10), value=0)
    selected_mon_exemp = max_mon_exemp * (pct_to_pension / 100)
    rem_honi_ptur = rem_sal_base * (1 - (pct_to_pension / 100))

    tab1, tab2, tab3 = st.tabs(["📜 קיבוע וקצבה", "🔄 דוח פריסה", "📊 כדאיות כלכלית"])

    with tab1:
        tax_no_ex, _ = calculate_income_tax(total_pension_from_funds, credit_points)
        tax_with_ex, _ = calculate_income_tax(max(0, total_pension_from_funds - selected_mon_exemp), credit_points)
        c1, c2, c3 = st.columns(3)
        c1.metric("קצבה נטו", f"₪{fmt_num(total_pension_from_funds - tax_with_ex)}")
        c2.metric("חיסכון מס חודשי", f"₪{fmt_num(tax_no_ex - tax_with_ex)}")
        c3.metric("הון פטור נותר", f"₪{fmt_num(rem_honi_ptur)}")

    with tab2:
        st.subheader("סימולציית פריסה עם הכנסות נוספות")
        other_income = st.number_input("הכנסה חודשית נוספת צפויה ברוטו (שכר עבודה וכו')", value=0)
        num_years = st.slider("שנות פריסה:", 1, 6, 6)
        
        ann_grant = taxable_grant_for_spread / num_years
        spread_rows = []
        total_tax_on_grant = 0
        
        for i in range(num_years):
            yr = retirement_date.year + i
            total_monthly = (total_pension_from_funds + other_income + (ann_grant/12))
            tax_total, m_rate = calculate_income_tax(max(0, total_monthly - selected_mon_exemp), credit_points)
            tax_base, _ = calculate_income_tax(max(0, (total_pension_from_funds + other_income) - selected_mon_exemp), credit_points)
            
            tax_on_grant_yr = (tax_total - tax_base) * 12
            total_tax_on_grant += tax_on_grant_yr
            
            spread_rows.append({
                "שנה": yr,
                "קצבה+שכר שנתי": (total_pension_from_funds + other_income) * 12,
                "חלק המענק השנה": ann_grant,
                "מס שנתי על המענק": tax_on_grant_yr,
                "מדרגת מס": f"{m_rate*100:.0f}%"
            })
        
        st.table(pd.DataFrame(spread_rows).style.format({c: "₪{:,.0f}" for c in ["קצבה+שכר שנתי", "חלק המענק השנה", "מס שנתי על המענק"]}))
        st.success(f"סך מס בפריסה: ₪{fmt_num(total_tax_on_grant)} | חיסכון מול מס מירבי: ₪{fmt_num((taxable_grant_for_spread * 0.47) - total_tax_on_grant)}")

    with tab3:
        st.subheader("בדיקת כדאיות: הון מול קצבה")
        # חישוב החיסכון המצטבר ב-15 שנה (180 חודשים)
        total_saving_15y = (tax_no_ex - tax_with_ex) * 180
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.write(f"אם תנצל את הפטור לקצבה, תחסוך ב-15 שנה מס בסך: **₪{fmt_num(total_saving_15y)}**")
            st.write(f"אם תמשוך כהון פטור, תקבל היום סכום נזיל של: **₪{fmt_num(rem_sal_base)}**")
        
        fig = go.Figure(data=[
            go.Bar(name='הון נזיל פטור (מידי)', x=['בחירה'], y=[rem_honi_ptur], marker_color='#2ecc71'),
            go.Bar(name='חיסכון מס בקצבה (15 שנה)', x=['בחירה'], y=[total_saving_15y], marker_color='#3498db')
        ])
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
