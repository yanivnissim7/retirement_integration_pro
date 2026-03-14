import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from fpdf import FPDF

# --- פונקציה ליצירת PDF ---
def create_pdf(emp_name, summary_data, funds):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Retirement Report: {emp_name}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.cell(200, 10, txt="Summary Results:", ln=True)
    for key, value in summary_data.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
    
    pdf.ln(10)
    pdf.cell(200, 10, txt="Funds Detail:", ln=True)
    for fund in funds:
        pdf.cell(200, 10, txt=f"{fund['name']} - {fund['type']}: Amount: {fund['amount']:,} | Coeff: {fund.get('coeff','N/A')}", ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

def main():
    st.set_page_config(page_title="אפקט - תכנון פרישה מלא", layout="wide")
    st.title("🏆 מערכת 'אפקט' - תכנון פרישה אסטרטגי")

    # --- SIDEBAR: גילאי 18-90 ---
    today = date.today()
    min_birth = today - relativedelta(years=90)
    max_birth = today - relativedelta(years=18)

    with st.sidebar:
        st.header("👤 פרטי לקוח")
        emp_name = st.text_input("שם מלא", "ישראל ישראלי")
        birth_date = st.date_input("תאריך לידה", value=date(1965, 11, 26), min_value=min_birth, max_value=max_birth)
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 11, 26))
        
        rdiff = relativedelta(ret_date, birth_date)
        age_val = rdiff.years + (rdiff.months/12)
        st.info(f"גיל בפרישה: {rdiff.years}.{rdiff.months}")

    # --- טאבים לניהול התהליך ---
    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "📉 פריסת מס וכדאיות", "📋 סיכום וייצוא"])

    with tab1:
        st.subheader("הזנת צבירות ומקדמים (מהפניקס/מנורה)")
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10}]

        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0})
            st.rerun()

        total_pension = 0.0
        total_capital = 0.0
        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
            fund['name'] = c1.text_input("שם קופה", fund.get('name',''), key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if fund.get('type')=='קצבתי' else 1, key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה (₪)", value=float(fund.get('amount',0)), key=f"a_{i}")
            if fund['type'] == 'קצבתי':
                fund['coeff'] = c4.number_input("מקדם ידני", value=float(fund.get('coeff',200)), key=f"c_{i}")
                total_pension += fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
            else:
                total_capital += fund['amount']

    with tab2:
        st.subheader("קיבוע זכויות (טופס 161ד)")
        col1, col2 = st.columns(2)
        with col1:
            grant_amount = st.number_input("מענקים פטורים שנתקבלו (ב-15 שנה אחרונות)", value=0.0)
            pension_limit = 9430  # תקרת קצבה מזכה 2024-2025 (לדוגמה)
            st.write(f"תקרת ההון הפטורה (2025): ₪882,648")
        with col2:
            is_commutation = st.checkbox("ביצוע היוון קצבה?")
            commutation_amount = st.number_input("סכום להיוון", value=0.0) if is_commutation else 0

    with tab3:
        st.subheader("פריסת מס וכדאיות")
        spread_years = st.slider("שנות פריסה (קדימה/אחורה)", 1, 6, 6)
        marginal_tax = st.slider("מדרגת מס משוערת בפרישה (%)", 10, 47, 20)
        
        st.info("בדיקת כדאיות: האם למשוך כספים כהון או כקצבה?")
        roi_pension = (total_pension * 12) / (total_capital if total_capital > 0 else 1)
        st.write(f"תשואת קצבה שנתית על ההון: {roi_pension:.2%}")

    with tab4:
        st.subheader("סיכום דוח פרישה")
        summary = {
            "Total Pension (Gross)": f"ILS {total_pension:,.2f}",
            "Total Capital": f"ILS {total_capital:,.0f}",
            "Retirement Age": f"{age_val:.2f}"
        }
        st.write(summary)
        
        if st.button("Generate & Download PDF Report"):
            try:
                pdf_data = create_pdf(emp_name, summary, st.session_state.funds)
                st.download_button(label="📥 Download PDF", data=pdf_data, file_name=f"Report_{emp_name}.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Error generating PDF: {e}. Note: Make sure 'fpdf' is installed.")

if __name__ == "__main__":
    main()
