import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- פרמטרים חוקיים 2026 ---
KITZBA_MAX = 9430 
SAL_PATOR_MAX_2026 = 976948  # סל הפטור המלא ל-2026 (לפני נסיגה)
MAX_WAGE_FOR_EXEMPT = 13750  # תקרת מענק פטור לכל שנת ותק

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
    st.set_page_config(page_title="אפקט - תיקון נוסחת נסיגה", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    # --- Sidebar ---
    with st.sidebar:
        st.header("👤 נתוני לקוח")
        agent_name = st.text_input("שם הסוכן", value="שם הסוכן")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        ret_date = st.date_input("תאריך פרישה", value=date(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=33.0, step=1.0) # כאן תשנה ל-50 ותראה את השינוי
        st.divider()
        st.header("💰 מענקים והכנסות")
        total_grant_bruto = st.number_input("סך מענקים ברוטו", value=968000)
        salary_for_exempt = st.number_input("שכר קובע (נניח המקסימום)", value=13750)
        pension_bruto = st.number_input("קצבה חודשית ברוטו", value=18200)

    # --- מנוע החישוב המתוקן ---
    # 1. חישוב המענק הפטור בפועל (מוגבל בותק ובתקרה שנתית)
    actual_exempt_grant = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    
    # 2. נוסחת הנסיגה: המענק הפטור כפול 1.35
    # הערה: אם היו פטורים ב-15 השנים האחרונות, הם מתווספים כאן (מוכפלים במקדם הצמדה של 32 שנות ותק אם רלוונטי)
    reduction_val = actual_exempt_grant * 1.35
    
    # 3. יתרת סל הפטור לקיבוע (2026)
    # סל הפטור המלא ב-2026 הוא 57.5% מ-180 תקרות הקצבה המזכה
    full_basket_2026 = KITZBA_MAX * 180 * 0.575
    remaining_basket_2026 = max(0, full_basket_2026 - reduction_val)
    
    # 4. יתרת סל הפטור לקיבוע (2028) - 67%
    full_basket_2028 = KITZBA_MAX * 180 * 0.67
    remaining_basket_2028 = max(0, full_basket_2028 - reduction_val)

    # --- תצוגה ---
    st.markdown(f"## דוח סיכום פרישה ל: {client_name}")
    
    t1, t2 = st.tabs(["📑 ניתוח קיבוע זכויות", "🔄 דוח פריסה"])
    
    with t1:
        st.subheader("השפעת הוותק על סל הפטור (נוסחת הנסיגה)")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("מענק פטור (סעיף 9(7א))", fmt_num(actual_exempt_grant))
        c2.metric("הפחתה מסל הפטור (נסיגה)", fmt_num(reduction_val))
        c3.metric("יתרת סל פטור לקצבה (2026)", fmt_num(remaining_basket_2026))

        st.divider()
        
        # חישוב נטו
        pct_to_pension = st.select_slider("ניצול הפטור לקצבה (%):", options=range(0,101,10), value=100)
        mon_ex_26 = (remaining_basket_2026 / 180) * (pct_to_pension / 100)
        
        tax_no_ex = calculate_income_tax(pension_bruto, credit_points)
        tax_with_ex = calculate_income_tax(max(0, pension_bruto - mon_ex_26), credit_points)
        
        res_a, res_b = st.columns(2)
        res_a.info(f"### נטו ללא פטור: {fmt_num(pension_bruto - tax_no_ex)}")
        res_b.success(f"### נטו אחרי קיבוע: {fmt_num(pension_bruto - tax_with_ex)}")
        
        st.write(f"💡 **הסבר:** בוותק של {seniority} שנים, המענק הפטור שלך הוא {fmt_num(actual_exempt_grant)}. "
                 f"הסכום הזה מוכפל ב-1.35 ומוריד {fmt_num(reduction_val)} מהזכות שלך לפטור על הקצבה.")

if __name__ == "__main__":
    main()
