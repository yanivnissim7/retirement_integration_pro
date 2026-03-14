import streamlit as st
import pandas as pd
from datetime import datetime

# --- פונקציית מנוע המקדמים (חולץ מתקנון הפניקס יולי 2024) ---
def get_phoenix_coefficient(gender, age, guarantee_months):
    # נתונים מנספח ו' - מקדם המרה לקצבת זקנה (ריבית 4.26%)
    # הטבלה כוללת את הערכים הנפוצים ביותר לפרישה
    data = {
        ('גבר', 67, 240): 191.65,
        ('גבר', 67, 180): 186.56,
        ('גבר', 67, 120): 183.55,
        ('גבר', 67, 60): 181.97,
        ('גבר', 67, 0): 181.49,
        ('גבר', 65, 240): 198.42,
        ('גבר', 60, 240): 219.10,
        ('אישה', 67, 240): 199.12,
        ('אישה', 64, 240): 208.45,
        ('אישה', 62, 240): 215.30,
        ('אישה', 60, 240): 222.80,
    }
    # מחזיר את המקדם המדויק או ברירת מחדל אם הגיל/מין לא בטבלה
    return data.get((gender, age, guarantee_months), 200.0)

def calculate_income_tax(monthly_income, credit_points=2.25):
    # מדרגות מס הכנסה 2024 (מעודכן)
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
    st.set_page_config(page_title="אפקט - מערכת פרישה אסטרטגית", layout="wide")
    
    # CSS ליישור לימין ותצוגה נקייה
    st.markdown("""<style> .main { direction: rtl; text-align: right; } div.stButton > button { width: 100%; } .stMetric { border: 1px solid #f0f2f6; padding: 10px; border-radius: 10px; } </style>""", unsafe_allow_html=True)
    
    st.title("🎯 מערכת פרישה אינטגרטיבית - אפקט")
    st.write("---")

    with st.sidebar:
        st.header("👤 פרטי הלקוח")
        client_name = st.text_input("שם הלקוח", "ישראל ישראלי")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        birth_date = st.date_input("תאריך לידה", value=datetime(1959, 2, 21))
        ret_date = st.date_input("תאריך פרישה", value=datetime(2026, 1, 1))
        
        # חישוב גיל פרישה
        age_at_ret = ret_date.year - birth_date.year
        st.info(f"גיל בפרישה: {age_at_ret}")
        
        st.divider()
        st.header("⚙️ הגדרות פנסיוניות")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        credit_points = st.number_input("נקודות זיכוי", 2.25)

    # 1. טבלת ריכוז צבירות
    st.subheader("📋 ריכוז צבירות ומקדמים (לפי תקנון הפניקס 2024)")
    
    if 'rows' not in st.session_state:
        st.session_state.rows = [{'קופה': 'הפניקס', 'צבירה': 1289354.0, 'הוני': 0.0}]

    edited_df = st.data_editor(pd.DataFrame(st.session_state.rows), num_rows="dynamic", use_container_width=True)
    
    # שליפת המקדם המעודכן מהמנוע הפנימי
    current_coeff = get_phoenix_coefficient(gender, age_at_ret, guarantee)
    
    # חישובים בטבלה
    edited_df['מקדם'] = current_coeff
    edited_df['קצבה חזויה ברוטו'] = edited_df['צבירה'] / edited_df['מקדם']
    
    st.write("---")
    
    # 2. סיכום נתונים כספיים
    total_bruto = edited_df['קצבה חזויה ברוטו'].sum()
    monthly_tax = calculate_income_tax(total_bruto, credit_points)
    total_neto = total_bruto - monthly_tax

    c1, c2, c3 = st.columns(3)
    c1.metric("סה''כ קצבה ברוטו", f"₪{total_bruto:,.0f}")
    c2.metric("מס הכנסה חודשי", f"₪{monthly_tax:,.0f}")
    c3.metric("קצבה נטו למשק בית", f"₪{total_neto:,.0f}")

    st.write("---")

    # 3. טאבים למחשבונים נוספים
    tab1, tab2 = st.tabs(["📊 ניתוח קצבה", "🔄 מחשבון פריסת פיצויים"])
    
    with tab1:
        st.subheader("פירוט קצבה")
        st.dataframe(edited_df[['קופה', 'צבירה', 'מקדם', 'קצבה חזויה ברוטו']].style.format({'צבירה': '{:,.0f}', 'קצבה חזויה ברוטו': '{:,.0f}'}))

    with tab2:
        st.subheader("סימולציית פריסת פיצויים (6 שנים)")
        grant_amount = st.number_input("סכום הפיצויים החייב במס", value=100000)
        annual_spread = grant_amount / 6
        st.write(f"סכום שנתי בפריסה: ₪{annual_spread:,.0f}")
        # כאן אפשר להוסיף טבלה עם חישוב מס לכל שנת פריסה

if __name__ == "__main__":
    main()
