import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
# שים לב: אנחנו משתמשים ב-fpdf2 שהיא הגרסה המעודכנת
from fpdf import FPDF

# --- פונקציות עזר ---
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
    st.set_page_config(page_title="אפקט - דוח סיכום פרישה", layout="wide")
    
    # --- Sidebar: קלט נתונים ---
    with st.sidebar:
        st.header("📋 מיתוג הדוח")
        agent_name = st.text_input("שם הסוכן / המתכנן", value="שם הסוכן")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        st.divider()
        st.header("👤 נתונים אישיים")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 1, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0, step=0.1)
        st.divider()
        st.header("💰 מענקים והכנסות")
        total_grant_bruto = st.number_input("סך מענקים ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע", value=13750)
        past_exempt_grants = st.number_input("פטורים ב-15 שנה", value=0)
        work_inc_ret_year = st.number_input("הכנסה ברוטו בשנת הפרישה", value=150000)

    # --- מנוע חישוב ---
    actual_exempt_161 = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant = total_grant_bruto - actual_exempt_161
    s_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_val = (actual_exempt_161 + past_exempt_grants) * 1.35 * s_factor
    
    sal_26 = max(0, (KITZBA_MAX * 0.575 * 180) - reduction_val)
    sal_28 = max(0, (KITZBA_MAX * 0.670 * 180) - reduction_val)

    # --- תצוגת האפליקציה ---
    st.markdown(f"<h1 style='text-align: center; color: #1E3A8A;'>דוח סיכום פרישה ל: {client_name}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>נערך על ידי: {agent_name}</p>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💰 קופות", "📑 קיבוע זכויות ונטו", "🔄 דוח פריסה", "📊 כדאיות"])

    with tab1:
        # כאן יבוא מנגנון הוספת הקופות המוכר...
        pension_total = st.number_input("הזן קצבה ברוטו משוערת מכל הקופות", value=15000.0)
        st.metric("סך קצבה חודשית ברוטו", fmt_num(pension_total))
        st.metric("סיכום הון הוני (מזומן)", fmt_num(0)) # כאן תחבר את סכום הקופות ההוניות

    with tab2:
        st.subheader("ניתוח השפעה על הנטו (קיבוע זכויות)")
        pct_to_pension = st.select_slider("אחוז הפטור לקצבה:", options=range(0,101,10), value=100)
        
        mon_ex_26 = (sal_26 / 180) * (pct_to_pension / 100)
        honi_ex_26 = sal_26 * (1 - (pct_to_pension / 100))
        
        tax_no_ex = calculate_income_tax(pension_total, credit_points)
        tax_with_ex = calculate_income_tax(max(0, pension_total - mon_ex_26), credit_points)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("נטו ללא שימוש בפטור", fmt_num(pension_total - tax_no_ex))
        c2.metric("נטו לאחר קיבוע זכויות", fmt_num(pension_total - tax_with_ex))
        c3.metric("תוספת חודשית לנטו", fmt_num(tax_no_ex - tax_with_ex))
        
        st.write(f"**בשנת 2028:** הפטור החודשי שלך יגדל ל-{fmt_num((sal_28/180)*(pct_to_pension/100))}")

    with tab3:
        st.subheader("דוח עזר למס הכנסה - פריסת המענק החייב")
        # טבלת פריסה עם עמודות מופרדות כפי שביקשת
        ann_grant = taxable_grant / 6
        data_spread = []
        for i in range(6):
            yr = ret_date.year + i
            inc_work = work_inc_ret_year if yr == ret_date.year else 0
            data_spread.append([yr, fmt_num(inc_work), fmt_num(pension_total*12), fmt_num(ann_grant)])
        
        df_spread = pd.DataFrame(data_spread, columns=["שנה", "הכנסה מעבודה", "הכנסה מקצבה", "חלק יחסי מענק"])
        st.table(df_spread)

    # --- ייצוא PDF ---
    st.divider()
    if st.button("📥 הפק דוח PDF סופי להורדה"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Retirement Report - {client_name}", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Agent: {agent_name}", ln=True, align='C')
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Monthly Net Addition: {fmt_num(tax_no_ex - tax_with_ex)}", ln=True)
        pdf.ln(20)
        
        disclaimer = "דיסקליימר: דוח זה מהווה סימולציה בלבד ואינו מחליף ייעוץ פנסיוני או מס. (חבות המס הסופית תיקבע על ידי פקיד השומה)."
        pdf.multi_cell(0, 10, txt=disclaimer)
        
        pdf_output = pdf.output()
        st.download_button(label="הורד דוח PDF", data=bytes(pdf_output), file_name="Retirement_Report.pdf", mime="application/pdf")

    st.markdown("---")
    st.markdown(f"<div style='direction: rtl; text-align: right; font-size: 12px; color: gray;'><b>דיסקליימר:</b> דוח זה מהווה סימולציה בלבד ואינו מהווה ייעוץ פנסיוני או ייעוץ מס מחליף. הנתונים מבוססים על המידע שנמסר על ידי המשתמש ועל הוראות החוק (כולל תיקון 190). חבות המס הסופית תיקבע אך ורק על ידי פקיד השומה.</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
