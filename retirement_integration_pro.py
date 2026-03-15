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
    for bracket, rate in brackets:
        if monthly_income > prev_bracket:
            taxable_in_bracket = min(monthly_income, bracket) - prev_bracket
            tax += taxable_in_bracket * rate
            prev_bracket = bracket
        else: break
    return max(0, tax - (credit_points * 250))

def main():
    st.set_page_config(page_title="אפקט - חישוב נסיגה מדויק", layout="wide")
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        ret_date = st.date_input("תאריך פרישה", value=date(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0, step=0.1)
        st.divider()
        st.header("💰 מענקים")
        total_grant_bruto = st.number_input("סך מענקים ברוטו", value=968000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        pension_bruto = st.number_input("קצבה ברוטו", value=18200)

    # --- מנוע חישוב מתוקן (נוסחת ה-32/ותק) ---
    # 1. חישוב המענק הפטור
    actual_exempt_161 = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    
    # 2. חישוב מקדם התיקון (רק אם ותק > 32)
    s_correction = 32 / seniority if seniority > 32 else 1.0
    
    # 3. נוסחת הנסיגה הסופית
    reduction_val = (actual_exempt_161 * 1.35) * s_correction

    # --- סל פטור 2026 ---
    full_basket_2026 = KITZBA_MAX * 180 * 0.575
    remaining_basket_2026 = max(0, full_basket_2026 - reduction_val)

    # --- תצוגה ---
    st.markdown(f"<h1 style='text-align: center;'>סימולציית פרישה: {client_name}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("ניתוח נסיגה (Recapture)")
        st.write(f"מענק פטור בפועל: **{fmt_num(actual_exempt_161)}**")
        if seniority > 32:
            st.write(f"מקדם תיקון ותק (32/{seniority}): **{s_correction:.3f}**")
        st.info(f"סך נסיגה מהסל: **{fmt_num(reduction_val)}**")

    with col2:
        st.subheader("תוצאה לקיבוע זכויות")
        st.write(f"יתרת סל פטור לקצבה: **{fmt_num(remaining_basket_2026)}**")
        
        # השפעה על הנטו
        mon_ex_26 = remaining_basket_2026 / 180
        tax_no_ex = calculate_income_tax(pension_bruto, credit_points)
        tax_with_ex = calculate_income_tax(max(0, pension_bruto - mon_ex_26), credit_points)
        
        st.success(f"תוספת חודשית לנטו: **{fmt_num(tax_no_ex - tax_with_ex)}**")

    # גרף להמחשה
    st.divider()
    f = go.Figure(data=[
        go.Bar(name='סל מלא', x=['2026'], y=[full_basket_2026], marker_color='lightgray'),
        go.Bar(name='נסיגה (קנס מענקים)', x=['2026'], y=[reduction_val], marker_color='red'),
        go.Bar(name='יתרה לפטור', x=['2026'], y=[remaining_basket_2026], marker_color='green')
    ])
    f.update_layout(barmode='stack', title="מבנה סל הפטור (תיקון 190)")
    st.plotly_chart(f)

if __name__ == "__main__":
    main()
