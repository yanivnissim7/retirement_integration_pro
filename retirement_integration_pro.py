import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- נתוני יסוד 2026 ---
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
    st.set_page_config(page_title="אפקט - חישוב ותק משופר", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    # --- Sidebar ---
    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 1, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        # שינוי בוותק כאן חייב להשפיע על הכל
        seniority = st.number_input("שנות ותק (משפיע על 161 ועל הנסיגה)", value=35.0, step=0.1)
        
        st.divider()
        st.header("💰 מענקים (161)")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("מענקים פטורים ב-15 שנה", value=0)

    # --- לוגיקת ותק קריטית ---
    # 1. פטור בטופס 161
    exempt_limit_per_year = min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT)
    max_exempt_grant_allowed = seniority * exempt_limit_per_year
    actual_exempt_grant = min(total_grant_bruto, max_exempt_grant_allowed)
    taxable_grant = total_grant_bruto - actual_exempt_grant

    # 2. נוסחת הנסיגה (קיזוז מסל הפטור)
    # כאן התיקון: המקדם 1.35 קטן ככל שהוותק עולה מעל 32
    seniority_factor = 32 / seniority if seniority > 32 else 1.0
    effective_reduction_multiplier = 1.35 * seniority_factor
    
    # סכום הקיזוז בפועל
    reduction_val = (actual_exempt_grant + past_exempt_grants) * effective_reduction_multiplier

    # --- חישובי סל פטור 2026/2028 ---
    sal_ptur_2026 = (KITZBA_MAX * 0.575) * 180
    rem_sal_2026 = max(0, sal_ptur_2026 - reduction_val)
    
    sal_ptur_2028 = (KITZBA_MAX * 0.670) * 180
    rem_sal_2028 = max(0, sal_ptur_2028 - reduction_val)

    st.markdown(f"<h1>אפקט - תכנון פרישה מבוסס ותק</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["💰 קופות", "📑 קיבוע זכויות", "🔄 פריסה", "📊 כדאיות 2026/28"])

    with tab1:
        v_pension = st.number_input("קצבה ותיקה/תקציבית:", value=0.0)
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'amount': 1000000.0, 'coeff': 197.10}]
        
        total_pension = v_pension
        for f in st.session_state.funds:
            total_pension += f['amount'] / f['coeff']
        st.metric("סה\"כ קצבה חודשית ברוטו", fmt_num(total_pension))

    with tab2:
        st.subheader("ניתוח סל הפטור לאחר נוסחת נסיגה")
        st.write(f"ותק שנבחר: **{seniority} שנים**")
        st.write(f"מקדם נסיגה אפקטיבי (במקום 1.35): **{effective_reduction_multiplier:.3f}**")
        
        pct_to_pension = st.select_slider("ניצול הפטור לקצבה:", options=range(0,101,10), value=100)
        mon_ex_26 = (rem_sal_2026 / 180) * (pct_to_pension / 100)
        
        c1, c2 = st.columns(2)
        c1.metric("סכום הקיזוז מהסל", fmt_num(reduction_val))
        c2.metric("יתרת הון פטורה (2026)", fmt_num(rem_sal_2026))

    with tab3:
        # פריסה - שימוש בנתוני הותק החדשים
        ann_tax_grant = taxable_grant / 6
        st.write(f"מענק חייב לפריסה: **{fmt_num(taxable_grant)}**")
        # (כאן תבוא הטבלה המפורטת מהגרסה הקודמת)

    with tab4:
        st.subheader("📊 השוואת כדאיות: השפעת הוותק והתיקון")
        
        # חישובי 15 שנה
        tax_no, _ = calculate_income_tax(total_pension, credit_points)
        
        # 2026
        ex_26 = rem_sal_2026 / 180
        tax_26, _ = calculate_income_tax(max(0, total_pension - ex_26), credit_points)
        save_26 = (tax_no - tax_26) * 180
        
        # 2028
        ex_28 = rem_sal_2028 / 180
        tax_28, _ = calculate_income_tax(max(0, total_pension - ex_28), credit_points)
        save_28 = (tax_no - tax_28) * 180

        col_a, col_b = st.columns(2)
        with col_a:
            st.write("### מצב 2026")
            fig1 = go.Figure(data=[
                go.Bar(name='הון פטור', x=['2026'], y=[rem_sal_2026], marker_color='#2ecc71', text=fmt_num(rem_sal_2026), textposition='auto'),
                go.Bar(name='חיסכון 15 שנה', x=['2026'], y=[save_26], marker_color='#3498db', text=fmt_num(save_26), textposition='auto')
            ])
            st.plotly_chart(fig1, use_container_width=True)
            
        with col_b:
            st.write("### מצב 2028")
            fig2 = go.Figure(data=[
                go.Bar(name='הון פטור', x=['2028'], y=[rem_sal_2028], marker_color='#27ae60', text=fmt_num(rem_sal_2028), textposition='auto'),
                go.Bar(name='חיסכון 15 שנה', x=['2028'], y=[save_28], marker_color='#2980b9', text=fmt_num(save_28), textposition='auto')
            ])
            st.plotly_chart(fig2, use_container_width=True)

if __name__ == "__main__":
    main()
