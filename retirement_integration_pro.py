import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

def main():
    st.set_page_config(page_title="אפקט - ניהול פרישה", layout="wide")
    st.title("🏆 סימולטור פרישה - אפקט")
    st.caption("כלי לריכוז נתונים והפקת דוח | הזנת מקדמים ידנית")

    # --- SIDEBAR: פרטי לקוח ופרמטרים כלליים ---
    with st.sidebar:
        st.header("👤 פרטי העמית")
        emp_name = st.text_input("שם העמית", "ישראל ישראלי")
        birth_date = st.date_input("תאריך לידה", value=date(1965, 11, 26), 
                                  min_value=date(1935, 1, 1), max_value=date(2008, 1, 1))
        ret_date = st.date_input("תאריך פרישה מתוכנן", value=date(2026, 11, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_name = st.text_input("שם בן/ת זוג", "")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=date(1968, 11, 26),
                                    min_value=date(1935, 1, 1), max_value=date(2008, 1, 1))
        
        # חישובי גיל בסיסיים לצורך התצוגה בלבד
        rdiff = relativedelta(ret_date, birth_date)
        age_at_ret = f"{rdiff.years}.{rdiff.months}"
        
        st.divider()
        st.info(f"גיל פרישה מתוכנן: {age_at_ret}")

    # --- MAIN SECTION: טבלת קופות והזנת נתונים ---
    st.subheader("💰 ריכוז קופות וצבירות")
    st.write("הזן את נתוני הצבירה והמקדמים המדויקים מהסימולטור המוסדי:")

    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10}]

    col_btn1, col_btn2 = st.columns([1, 5])
    if col_btn1.button("➕ הוסף קופה"):
        st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0})
        st.rerun()
    if col_btn2.button("🗑️ נקה הכל"):
        st.session_state.funds = []
        st.rerun()

    total_pension = 0.0
    total_capital = 0.0

    for i, fund in enumerate(st.session_state.funds):
        with st.expander(f"קופה {i+1}: {fund['name'] if fund['name'] else 'חדשה'}", expanded=True):
            c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
            fund['name'] = c1.text_input("שם הקופה / יצרן", fund['name'], key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג כסף", ["קצבתי", "הוני"], index=0 if fund['type'] == 'קצבתי' else 1, key=f"t_{i}")
            fund['amount'] = c3.number_input("סכום צבירה (₪)", value=fund['amount'], step=1000.0, key=f"a_{i}")
            
            if fund['type'] == 'קצבתי':
                fund['coeff'] = c4.number_input("מקדם (הזנה ידנית)", value=fund['coeff'], step=0.01, format="%.2f", key=f"c_{i}")
                pension_contribution = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                total_pension += pension_contribution
                st.write(f"👉 **קצבה חזויה מקופה זו:** ₪{pension_contribution:,.2f}")
            else:
                total_capital += fund['amount']
                c4.write("")
                st.write("💰 **כסף הוני - לא נכלל בחישוב הקצבה**")

    # --- SUMMARY: סיכום דוח ---
    st.divider()
    st.subheader(f"📊 סיכום דוח פרישה עבור: {emp_name}")
    
    res1, res2, res3 = st.columns(3)
    res1.metric("סה\"כ קצבה חודשית (ברוטו)", f"₪{total_pension:,.2f}")
    res2.metric("סה\"כ הון חד פעמי", f"₪{total_capital:,.0f}")
    res3.metric("סה\"כ צבירה בניהול", f"₪{(total_capital + sum(f['amount'] for f in st.session_state.funds if f['type']=='קצבתי')):,.0f}")

    # אפשרות להערות מקצועיות
    st.divider()
    notes = st.text_area("הערות והמלצות למתכנן הפרישה:", "בהתאם למסלול שנבחר בסימולטור המוסדי...")

if __name__ == "__main__":
    main()
