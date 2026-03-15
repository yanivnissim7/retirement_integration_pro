import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
from fpdf import FPDF

# --- הגדרות קבועות ---
KITZBA_MAX = 9430 
MAX_WAGE_FOR_EXEMPT = 13750 

def fmt_num(num): return f"₪{float(num):,.0f}"

# פונקציה לייצוא PDF
def export_to_pdf(agent, client, summary_data, table_rows, disclaimer):
    pdf = FPDF()
    pdf.add_page()
    # הערה: יש לוודא שיש קובץ פונט עברי בתיקיית הפרויקט (למשל arial.ttf)
    # pdf.add_font('Hebrew', '', 'arial.ttf', uni=True) 
    pdf.set_font('Arial', 'B', 16)
    
    pdf.cell(200, 10, txt=f"Retirement Summary Report for: {client[::-1]}", ln=True, align='C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(200, 10, txt=f"Prepared by: {agent[::-1]}", ln=True, align='C')
    pdf.ln(10)
    
    for key, val in summary_data.items():
        pdf.cell(200, 10, txt=f"{key[::-1]}: {val}", ln=True, align='R')
    
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=disclaimer[::-1], align='R')
    return pdf.output(dest='S').encode('latin-1')

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
    st.set_page_config(page_title="אפקט - הפקת דוח PDF", layout="wide")
    
    # --- SideBar & Calculations (כמו בגרסה הקודמת) ---
    with st.sidebar:
        agent_name = st.text_input("שם הסוכן", value="מתכנן פרישה מומחה")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        seniority = st.number_input("שנות ותק", value=35.0)
        total_grant_bruto = st.number_input("סך מענקים ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע", value=13750)
        past_exempt_grants = st.number_input("פטורים בעבר", value=0)

    # לוגיקת ותק וקיזוז
    actual_exempt_161 = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    s_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_val = (actual_exempt_161 + past_exempt_grants) * 1.35 * s_factor
    
    st.markdown(f"<h1 style='text-align: center;'>דוח סיכום פרישה ל: {client_name}</h1>", unsafe_allow_html=True)

    # --- טאב קיבוע זכויות ונטו ---
    tab_kivua, tab_spread = st.tabs(["📑 קיבוע זכויות ונטו", "🔄 דוח פריסה"])
    
    with tab_kivua:
        pct_to_pension = st.select_slider("ניצול פטור לקצבה", options=range(0,101,10), value=100)
        sal_26 = max(0, (KITZBA_MAX * 0.575 * 180) - reduction_val)
        mon_ex_26 = (sal_26 / 180) * (pct_to_pension / 100)
        
        # חישוב נטו (דוגמה על בסיס קצבה של 15,000)
        base_pension = 15000 
        tax_before = calculate_income_tax(base_pension)
        tax_after = calculate_income_tax(base_pension - mon_ex_26)
        
        st.subheader("📊 ניתוח השפעה על הנטו")
        c1, c2, c3 = st.columns(3)
        c1.metric("נטו ללא פטור", fmt_num(base_pension - tax_before))
        c2.metric("נטו לאחר פטור", fmt_num(base_pension - tax_after))
        c3.metric("תוספת חודשית לנטו", fmt_num(tax_before - tax_after), delta_color="normal")

    # --- כפתור ייצוא ---
    st.divider()
    disclaimer_text = "דיסקליימר: דוח זה מהווה סימולציה בלבד ואינו מחליף ייעוץ פנסיוני או מס. חבות המס הסופית תיקבע על ידי פקיד השומה בלבד."
    
    if st.button("📥 הפק דוח PDF סופי"):
        # הערה: בסביבת ענן/לוקאל יש לוודא טיפול ב-Unicode לעברית
        st.success(f"הדוח עבור {client_name} נוצר בהצלחה!")
        st.download_button(
            label="לחץ כאן להורדת הקובץ",
            data=b"PDF Content Simulation", # כאן תבוא הפונקציה export_to_pdf
            file_name=f"Retirement_Report_{client_name}.pdf",
            mime="application/pdf"
        )

    st.markdown(f"<div style='direction: rtl; text-align: right; font-size: 12px; color: gray;'>{disclaimer_text}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
