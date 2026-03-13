import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import openpyxl # ספרייה לקריאת אקסל

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

# פונקציה לחיבור לאקסל המוסדי
def get_coefficient_from_excel(gender, birth_date, ret_year, assets, coverage_pct, guarantee_months):
    try:
        wb = openpyxl.load_workbook('simulator_prisha.xlsx', data_only=False)
        sheet = wb['חישוב זקנה']
        
        # הזנת נתונים לתאים לפי המיפוי מהצילום
        sheet['C14'] = birth_date.strftime('%d/%m/%Y') # תאריך לידה
        sheet['C13'] = ret_year # שנת פרישה
        sheet['C15'] = "זכר" if gender == "גבר" else "נקבה"
        sheet['C18'] = assets # סכום צבירה
        sheet['C20'] = coverage_pct / 100 # שיעור לבת זוג
        sheet['C21'] = guarantee_months # תקופת הבטחה
        
        # שמירה זמנית לצורך חישוב נוסחאות (בזיכרון)
        wb.save('temp_sim.xlsx')
        
        # טעינה מחדש לקבלת ערכים מחושבים
        wb_res = openpyxl.load_workbook('temp_sim.xlsx', data_only=True)
        sheet_res = wb_res['חישוב זקנה']
        
        coeff = sheet_res['C28'].value
        pension = sheet_res['C29'].value
        
        return coeff, pension
    except Exception as e:
        st.error(f"שגיאה בחיבור לאקסל: {e}")
        return None, None

def main():
    st.set_page_config(page_title="מערכת פרישה אינטגרטיבית - אפקט", layout="wide")
    st.markdown("""<style> .main, .stTabs, div[data-testid="stMetricValue"], .stMarkdown, p, h1, h2, h3, label { direction: rtl; text-align: right !important; } .stTable { direction: rtl; } </style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 נתוני לקוח לסנכרון")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        birth_date = st.date_input("תאריך לידה", value=datetime(1960, 1, 1))
        coverage_pct = st.slider("שיעור קצבת שאירים לבת זוג (%)", 0, 100, 60)
        guarantee_months = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        
        st.divider()
        st.header("💰 מענקים")
        total_grant_bruto = st.number_input("סך מענק ברוטו", value=0)
        seniority = st.number_input("שנות ותק", value=1.0)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)

    st.title("מערכת פרישה פרו - סנכרון מוסדי 🔄")

    # טבלת קופות
    st.subheader("📋 ריכוז קופות")
    if 'rows' not in st.session_state:
        st.session_state.rows = [{'קופה': 'מקפת', 'קצבתי': 1000000.0, 'הוני': 0.0, 'מקדם': 200.0}]

    edited_df = st.data_editor(pd.DataFrame(st.session_state.rows), num_rows="dynamic", use_container_width=True)

    if st.button("🔄 סנכרן מקדמים וקצבאות מול מחשבון אקסל"):
        with st.spinner("מתחבר למחשבון המוסדי..."):
            new_rows = []
            for index, row in edited_df.iterrows():
                # ביצוע החישוב באקסל עבור כל שורה קצבתית
                coeff, _ = get_coefficient_from_excel(gender, birth_date, 2026, row['קצבתי'], coverage_pct, guarantee_months)
                if coeff:
                    row['מקדם'] = round(coeff, 2)
                new_rows.append(row)
            st.session_state.rows = new_rows
            st.rerun()

    # חישוב תוצאות סופיות
    edited_df['קצבה חזויה'] = edited_df.apply(lambda row: row['קצבתי'] / row['מקדם'] if row['מקדם'] > 0 else 0, axis=1)
    total_pension = edited_df['קצבה חזויה'].sum()
    
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("סה''כ קצבה ברוטו מחושבת", f"₪{fmt_num(total_pension)}")
    c2.metric("מקדם משוקלל", f"{total_pension / (edited_df['קצבתי'].sum() / 100) if total_pension > 0 else 0:.2f}")

    # המשך לוגיקת המס והפריסה (כפי שהיה בקוד הקודם)
    # ... (כאן מגיע שאר הקוד של חישובי הפטור והפריסה)

if __name__ == "__main__":
    main()
