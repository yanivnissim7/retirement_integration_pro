import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

def main():
    st.set_page_config(page_title="אפקט - תכנון פרישה אסטרטגי", layout="wide")
    st.title("🏆 מערכת 'אפקט' - תכנון פרישה מלא")

    # --- הגדרות טווח גילאים (18-90) ---
    today = date.today()
    min_birth = today - relativedelta(years=90)
    max_birth = today - relativedelta(years=18)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 פרטי לקוח")
        emp_name = st.text_input("שם מלא", "ישראל ישראלי")
        birth_date = st.date_input("תאריך לידה", value=date(1965, 11, 26), min_value=min_birth, max_value=max_birth)
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 11, 26))
        
        rdiff = relativedelta(ret_date, birth_date)
        st.info(f"גיל בפרישה: {rdiff.years}.{rdiff.months}")
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=date(1968, 11, 26), min_value=min_birth, max_value=max_birth)

    # --- טאבים לניהול התהליך ---
    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות (161ד)", "📉 פריסת מס וכדאיות", "📋 סיכום דוח"])

    with tab1:
        st.subheader("ריכוז צבירות ומקדמים (הזנה ידנית)")
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10}]

        if st.button("➕ הוסף קופה/קרן"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0})
            st.rerun()

        total_pension = 0.0
        total_capital = 0.0
        
        for i, fund in enumerate(st.session_state.funds):
            with st.expander(f"קופה {i+1}: {fund.get('name','')}", expanded=True):
                c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
                fund['name'] = c1.text_input("שם קופה", fund.get('name',''), key=f"n_{i}")
                fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if fund.get('type')=='קצבתי' else 1, key=f"t_{i}")
                fund['amount'] = c3.number_input("צבירה (₪)", value=float(fund.get('amount',0)), key=f"a_{i}")
                
                if fund['type'] == 'קצבתי':
                    fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
                    total_pension += fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                else:
                    total_capital += fund['amount']

    with tab2:
        st.subheader("קיבוע זכויות - סל הפטור (טופס 161ד)")
        c1, c2 = st.columns(2)
        with c1:
            grant_amount = st.number_input("מענקים פטורים שנתקבלו (15 שנה אחרונות)", value=0.0)
            st.write("תקרת הפטור ל-2025: ₪882,648")
        with c2:
            multiplier = 1.35
            consumed_limit = grant_amount * multiplier
            remaining_limit = max(0, 882648 - consumed_limit)
            st.metric("יתרת סל פטור להיוון/קצבה", f"₪{remaining_limit:,.0f}")

    with tab3:
        st.subheader("פריסת מס וכדאיות כלכלית")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            spread_type = st.radio("סוג פריסה מבוקש", ["קדימה (על מענק פרישה)", "אחורה (על הפרשי שכר)"])
            spread_years = st.slider("מספר שנות פריסה", 1, 6, 6)
        with col_f2:
            marginal_tax = st.number_input("מדרגת מס שולית צפויה (%)", value=20)
            st.info("בדיקת כדאיות: יחס המרה קצבה מול הון")
            if total_capital > 0:
                annuity_ratio = (total_pension * 12) / total_capital
                st.write(f"תשואת קצבה שנתית: {annuity_ratio:.2%}")

    with tab4:
        st.subheader("סיכום נתוני פרישה")
        res1, res2, res3 = st.columns(3)
        res1.metric("קצבה חודשית ברוטו", f"₪{total_pension:,.2f}")
        res2.metric("סה\"כ הון חד פעמי", f"₪{total_capital:,.0f}")
        res3.metric("יתרת פטור בקיבוע", f"₪{remaining_limit:,.0f}")

        st.divider()
        if st.button("💾 שמור נתונים לייצוא"):
            df_export = pd.DataFrame(st.session_state.funds)
            csv = df_export.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 הורד קובץ נתונים לאקסל", data=csv, file_name=f"Report_{emp_name}.csv")

if __name__ == "__main__":
    main()
