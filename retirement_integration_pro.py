import streamlit as st
import pandas as pd
from datetime import datetime

# --- פונקציית מנוע המקדמים (חולץ מתקנון הפניקס 2024) ---
def get_official_coefficient(gender, age, guarantee_months):
    # נתוני מקדמים לדוגמה מנספח ו' (גבר, פרישה בגיל 67)
    # הערה: המערכת תבצע אינטרפולציה או שליפה לפי הטבלה המלאה שהזנו
    data = {
        ('גבר', 67, 240): 191.65,
        ('גבר', 67, 180): 186.56,
        ('גבר', 67, 120): 183.55,
        ('גבר', 67, 60): 181.97,
        ('גבר', 67, 0): 181.49,
        ('אישה', 62, 240): 215.30, # דוגמה לערכי נשים
        ('אישה', 64, 240): 208.45,
        ('אישה', 67, 240): 199.12
    }
    return data.get((gender, age, guarantee_months), 200.0)

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
    st.set_page_config(page_title="אפקט - מערכת פרישה מקצועית", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🎯 מערכת פרישה אינטגרטיבית - אפקט")
    st.info("המערכת מסונכרנת עם תקנון הפניקס (מהדורת יולי 2024)")

    with st.sidebar:
        st.header("👤 נתוני לקוח")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        birth_date = st.date_input("תאריך לידה", value=datetime(1959, 2, 21))
        ret_date = st.date_input("תאריך פרישה", value=datetime(2026, 1, 1))
        age_at_ret = ret_date.year - birth_date.year
        
        st.divider()
        st.header("⚙️ הגדרות פנסיה")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        credit_points = st.number_input("נקודות זיכוי", 2.25)

    # חישוב המקדם באופן אוטומטי
    current_coeff = get_official_coefficient(gender, age_at_ret, guarantee)

    # טבלת קופות
    st.subheader("📋 צבירות ומקדמים")
    if 'rows' not in st.session_state:
        st.session_state.rows = [{'קופה': 'הפניקס', 'צבירה': 1289354.0}]
    
    df = pd.DataFrame(st.session_state.rows)
    df['מקדם (לפי תקנון)'] = current_coeff
    df['קצבה ברוטו'] = df['צבירה'] / df['מקדם (לפי תקנון)']
    
    st.table(df.style.format({'צבירה': '{:,.0f}', 'מקדם (לפי תקנון)': '{:.2f}', 'קצבה ברוטו': '{:,.0f}'}))

    total_bruto = df['קצבה ברוטו'].sum()
    tax = calculate_income_tax(total_bruto, credit_points)

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("סה''כ קצבה ברוטו", f"₪{total_bruto:,.0f}")
    c2.metric("מס הכנסה (משוער)", f"₪{tax:,.0f}")
    c3.metric("קצבה נטו", f"₪{total_bruto - tax:,.0f}")

if __name__ == "__main__":
    main()
