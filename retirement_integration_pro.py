import streamlit as st
import pandas as pd
import openpyxl
import os
from datetime import datetime

# --- הגדרות קבועות ---
SAL_PTUR_MAX = 976005 

def fmt_num(num): 
    try: return f"₪{float(num):,.0f}"
    except: return "0"

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

def get_coefficient_from_excel(gender, birth_date, assets, coverage_pct, guarantee_months):
    try:
        source_file = 'simulator_prisha.xlsm'
        if not os.path.exists(source_file):
            return "File Missing", None
        
        # כתיבה לקובץ
        wb = openpyxl.load_workbook(source_file, keep_vba=True)
        sheet = wb.active
        sheet['C14'] = birth_date.strftime('%d/%m/%Y')
        sheet['C15'] = "נקבה" if gender == "אישה" else "זכר"
        sheet['C18'] = float(assets)
        sheet['C20'] = float(coverage_pct) / 100
        sheet['C21'] = int(guarantee_months)
        
        temp_file = 'temp_sim_result.xlsm'
        wb.save(temp_file)
        
        # קריאה מחדש
        wb_res = openpyxl.load_workbook(temp_file, data_only=True)
        res_sheet = wb_res.active
        coeff = res_sheet['C27'].value
        
        # אם קיבלנו None או נוסחה, סימן שהשרת לא מחשב
        if coeff is None or isinstance(coeff, str):
            return "Calc Error", None
            
        return coeff, None
    except Exception as e:
        return f"Error: {str(e)}", None

def main():
    st.set_page_config(page_title="אפקט - תכנון פרישה אסטרטגי", layout="wide")
    
    # עיצוב RTL ולוגו
    st.markdown("""<style> .main { direction: rtl; text-align: right; } div.stButton > button { width: 100%; border-radius: 5px; background-color: #007bff; color: white; } </style>""", unsafe_allow_html=True)
    
    st.title("🎯 מערכת פרישה אינטגרטיבית - אפקט")
    st.write("---")

    with st.sidebar:
        st.header("👤 פרטי הלקוח")
        client_name = st.text_input("שם הלקוח", "ישראל ישראלי")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        birth_date = st.date_input("תאריך לידה", value=datetime(1959, 2, 21))
        credit_points = st.number_input("נקודות זיכוי", 2.25)
        
        st.divider()
        st.header("⚙️ הגדרות פנסיה")
        guarantee = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        coverage = st.slider("שאירים (%)", 0, 100, 0)

    # טבלת ריכוז קופות
    st.subheader("📋 ריכוז צבירות ומקדמים")
    if 'rows' not in st.session_state:
        st.session_state.rows = [{'קופה': 'הפניקס', 'צבירה': 1289354.0, 'מקדם': 191.65}]

    edited_df = st.data_editor(pd.DataFrame(st.session_state.rows), num_rows="dynamic", use_container_width=True)

    if st.button("🔄 בצע סנכרון מול מחשבון הפניקס"):
        new_rows = []
        for _, row in edited_df.iterrows():
            with st.spinner(f"מחשב עבור {row['קופה']}..."):
                res, _ = get_coefficient_from_excel(gender, birth_date, row['צבירה'], coverage, guarantee)
                if isinstance(res, (float, int)):
                    row['מקדם'] = round(res, 2)
                    st.success(f"המקדם עודכן ל-{row['מקדם']}")
                else:
                    st.error(f"לא ניתן לסנכרן אוטומטית: {res}. הזן מקדם ידנית.")
            new_rows.append(row)
        st.session_state.rows = new_rows

    # חישובי המשך - נטו ופריסה
    df = pd.DataFrame(st.session_state.rows)
    total_pension_bruto = (df['צבירה'] / df['מקדם']).sum() if not df.empty else 0
    
    st.divider()
    
    tab1, tab2, tab3 = st.tabs(["📊 חישוב קצבה ונטו", "🔄 פריסת פיצויים", "💰 סל פטור"])

    with tab1:
        tax, marginal = calculate_income_tax(total_pension_bruto, credit_points)
        c1, c2, c3 = st.columns(3)
        c1.metric("קצבה ברוטו", fmt_num(total_pension_bruto))
        c2.metric("מס הכנסה", fmt_num(tax))
        c3.metric("קצבה נטו", fmt_num(total_pension_bruto - tax))

    with tab2:
        st.write("טבלת פריסה תופיע כאן...")

    with tab3:
        st.write("חישוב סל פטור (נוסחת הנסיגה) יופיע כאן...")

if __name__ == "__main__":
    main()
