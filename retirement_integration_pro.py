import streamlit as st
import pandas as pd
import openpyxl
import os
from datetime import datetime

# --- פונקציית סנכרון מדויקת לפי הצילום הצהוב ---
def get_coefficient_from_excel(gender, birth_date, assets, coverage_pct, guarantee_months):
    try:
        source_file = 'simulator_prisha.xlsm'
        if not os.path.exists(source_file): 
            return None, None
        
        # טעינה
        wb = openpyxl.load_workbook(source_file, keep_vba=True, data_only=False)
        sheet = wb.active 
        
        # הזנה לתאים לפי הצילום (מיפוי הפניקס)
        sheet['C14'] = birth_date.strftime('%d/%m/%Y') # תאריך לידה
        sheet['C15'] = "נקבה" if gender == "אישה" else "זכר"
        sheet['C18'] = float(assets) # סכום צבירה
        sheet['C20'] = float(coverage_pct) / 100 # שיעור לשאירים
        sheet['C21'] = int(guarantee_months) # תקופת הבטחה
        
        # שמירה וקריאה מחדש של הערכים המחושבים
        temp_path = 'temp_result.xlsm'
        wb.save(temp_path)
        
        wb_res = openpyxl.load_workbook(temp_path, data_only=True)
        res_sheet = wb_res.active
        
        # לפי הצילום הצהוב: C27 זה המקדם, C28 זה הקצבה
        coeff = res_sheet['C27'].value
        pension = res_sheet['C28'].value
        
        return coeff, pension
    except Exception as e:
        st.error(f"שגיאת סנכרון: {e}")
        return None, None

def main():
    st.set_page_config(page_title="אפקט - מערכת פרישה מלאה", layout="wide")
    
    # CSS ליישור לימין
    st.markdown("""<style> .main, .stTabs, div[data-testid="stMetricValue"], .stMarkdown, p, h1, h2, h3, label { direction: rtl; text-align: right !important; } .stTable { direction: rtl; } </style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 נתוני לקוח")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        birth_date = st.date_input("תאריך לידה", value=datetime(1959, 2, 21))
        ret_date = st.date_input("תאריך פרישה", value=datetime(2025, 8, 1))
        
        st.divider()
        st.header("⚙️ הגדרות הפניקס")
        coverage_pct = st.slider("שיעור לשאירים (%)", 0, 100, 0)
        guarantee_months = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)

    st.title("מערכת פרישה אינטגרטיבית - אפקט")

    # טבלת קופות
    if 'rows' not in st.session_state:
        st.session_state.rows = [{'קופה': 'הפניקס', 'קצבתי': 1289354.0, 'הוני': 0.0, 'מקדם': 191.65}]

    edited_df = st.data_editor(pd.DataFrame(st.session_state.rows), num_rows="dynamic", use_container_width=True)

    if st.button("🔄 סנכרן נתונים מהמחשבון הצהוב"):
        with st.spinner("מתחבר לאקסל של הפניקס..."):
            new_rows = []
            for _, row in edited_df.iterrows():
                coeff, _ = get_coefficient_from_excel(gender, birth_date, row['קצבתי'], coverage_pct, guarantee_months)
                if coeff and isinstance(coeff, (int, float)): 
                    row['מקדם'] = round(float(coeff), 2)
                new_rows.append(row)
            st.session_state.rows = new_rows
            st.rerun()

    # חישוב קצבה חזויה
    edited_df['קצבה חזויה'] = edited_df.apply(lambda row: row['קצבתי'] / row['מקדם'] if row['מקדם'] > 0 else 0, axis=1)
    total_pension = edited_df['קצבה חזויה'].sum()
    
    st.metric("סה''כ קצבה ברוטו (מחושב)", f"₪{total_pension:,.0f}")

    # טאבים למחשבונים שחזרו
    tab1, tab2 = st.tabs(["📊 ניתוח נטו", "🔄 פריסת מענקים"])
    with tab1:
        st.write("כאן יופיעו חישובי הנטו והמס...")
    with tab2:
        st.write("כאן תופיע טבלת הפריסה...")

if __name__ == "__main__":
    main()
