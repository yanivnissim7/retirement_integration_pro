import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import openpyxl

# --- נתוני יסוד 2026 ---
SAL_PTUR_MAX = 976005 
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

# פונקציית סנכרון מעודכנת לקובץ XLSM
def get_coefficient_from_excel(gender, birth_date, ret_year, assets, coverage_pct, guarantee_months):
    try:
        # טעינת קובץ עם תמיכה ב-VBA
        wb = openpyxl.load_workbook('simulator_prisha.xlsm', keep_vba=True, data_only=False)
        sheet = wb['חישוב זקנה']
        
        # הזנת נתונים
        sheet['C14'] = birth_date.strftime('%d/%m/%Y')
        sheet['C13'] = ret_year
        sheet['C15'] = "זכר" if gender == "גבר" else "נקבה"
        sheet['C18'] = assets
        sheet['C20'] = coverage_pct / 100
        sheet['C21'] = guarantee_months
        
        # שמירה זמנית בסיומת XLSM
        wb.save('temp_sim.xlsm')
        
        # קריאת הערכים המחושבים
        wb_res = openpyxl.load_workbook('temp_sim.xlsm', data_only=True)
        sheet_res = wb_res['חישוב זקנה']
        
        coeff = sheet_res['C28'].value
        pension = sheet_res['C29'].value
        
        return coeff, pension
    except Exception as e:
        st.error(f"שגיאה בסנכרון XLSM: {e}")
        return None, None

def main():
    st.set_page_config(page_title="אפקט - מערכת פרישה משולבת", layout="wide")
    st.markdown("""<style> .main, .stTabs, div[data-testid="stMetricValue"], .stMarkdown, p, h1, h2, h3, label { direction: rtl; text-align: right !important; } .stTable { direction: rtl; } </style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 פרטי לקוח")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        birth_date = st.date_input("תאריך לידה", value=datetime(1960, 1, 1))
        ret_date = st.date_input("תאריך פרישה", value=datetime(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        
        st.divider()
        st.header("⚙️ הגדרות קרן פנסיה")
        coverage_pct = st.slider("שיעור לשאירים (%)", 0, 100, 60)
        guarantee_months = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)

    st.title("דוח תכנון פרישה אסטרטגי - אפקט סוכנות לביטוח")

    # 1. טבלת קופות
    st.subheader("📋 ריכוז נכסים וצבירות")
    if 'rows' not in st.session_state:
        st.session_state.rows = [{'קופה': 'מקפת', 'קצבתי': 1000000.0, 'הוני': 0.0, 'מקדם': 200.0}]

    edited_df = st.data_editor(pd.DataFrame(st.session_state.rows), num_rows="dynamic", use_container_width=True)

    if st.button("🔄 סנכרן מקדמים מול המחשבון המוסדי (XLSM)"):
        with st.spinner("מבצע סימולציה באקסל..."):
            new_rows = []
            for _, row in edited_df.iterrows():
                coeff, _ = get_coefficient_from_excel(gender, birth_date, ret_date.year, row['קצבתי'], coverage_pct, guarantee_months)
                if coeff: row['מקדם'] = round(float(coeff), 2)
                new_rows.append(row)
            st.session_state.rows = new_rows
            st.rerun()

    # חישובי המשך
    edited_df['קצבה חזויה'] = edited_df.apply(lambda row: row['קצבתי'] / row['מקדם'] if row['מקדם'] > 0 else 0, axis=1)
    total_pension = edited_df['קצבה חזויה'].sum()
    
    # חישובי פטור (סל פטור)
    seniority = st.sidebar.number_input("שנות ותק", value=30.0)
    total_grant = st.sidebar.number_input("סך מענקים חייבים ופטורים", value=0)
    actual_exempt_now = min(total_grant, seniority * 13750)
    taxable_grant = total_grant - actual_exempt_now
    reduction = (actual_exempt_now * 1.35) * (32/seniority if seniority > 32 else 1)
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction)
    max_mon_exemp = rem_sal_base / 180

    st.divider()
    
    # 2. מחשבונים בטאבים
    pct_to_pension = st.select_slider("ניצול סל הפטור לטובת הקצבה:", options=range(0, 101, 10), value=0)
    selected_mon_exemp = max_mon_exemp * (pct_to_pension / 100)

    tab1, tab2, tab3 = st.tabs(["📊 ניתוח קצבה ונטו", "🔄 פריסת מענקים", "📋 כדאיות הון מול קצבה"])

    with tab1:
        tax_no_ex, _ = calculate_income_tax(total_pension, credit_points)
        tax_with_ex, _ = calculate_income_tax(max(0, total_pension - selected_mon_exemp), credit_points)
        c1, c2, c3 = st.columns(3)
        c1.metric("קצבה נטו חזויה", fmt_num(total_pension - tax_with_ex), f"חיסכון: {fmt_num(tax_no_ex - tax_with_ex)}")
        c2.metric("מס הכנסה חודשי", fmt_num(tax_with_ex))
        c3.metric("סכום הוני פטור נותר", fmt_num(rem_sal_base * (1 - pct_to_pension/100)))

    with tab2:
        is_after_oct = ret_date.month >= 10
        start_yr = st.selectbox("שנת תחילת פריסה:", [ret_date.year, ret_date.year + 1], index=1 if is_after_oct else 0)
        num_yrs = st.slider("שנות פריסה:", 1, 6, 6)
        ann_grant = taxable_grant / num_yrs
        spread_rows = []
        for i in range(num_yrs):
            yr = start_yr + i
            t_total, m_rate = calculate_income_tax(max(0, total_pension + (ann_grant/12) - selected_mon_exemp), credit_points)
            spread_rows.append({"שנה": yr, "ברוטו שנתי": (total_pension * 12) + ann_grant, "מס": t_total * 12, "מדרגת מס": f"{m_rate*100:.0f}%"})
        st.table(pd.DataFrame(spread_rows))

    with tab3:
        st.write("### ריכוז הון נזיל בפרישה")
        honi_table = pd.DataFrame({
            "מקור": ["יתרות הוניות מקופות", "יתרת סל פטור הוני"],
            "סכום": [fmt_num(edited_df['הוני'].sum()), fmt_num(rem_sal_base * (1 - pct_to_pension/100))]
        })
        st.table(honi_table)

if __name__ == "__main__":
    main()
