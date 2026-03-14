import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

def main():
    st.set_page_config(page_title="אפקט - ניהול פרישה", layout="wide")
    st.title("🏆 סימולטור פרישה - אפקט")
    st.caption("ריכוז נתוני פרישה | הזנת מקדמים ידנית מהמוסדיים")

    # --- הגדרות טווח גילאים (18-90) ---
    today = date.today()
    min_birth = today - relativedelta(years=90)
    max_birth = today - relativedelta(years=18)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 פרטי העמית")
        emp_name = st.text_input("שם העמית", "ישראל ישראלי")
        birth_date = st.date_input("תאריך לידה עמית", value=date(1965, 11, 26), 
                                  min_value=min_birth, max_value=max_birth)
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 11, 26))
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=date(1968, 11, 26),
                                    min_value=min_birth, max_value=max_birth)
        
        rdiff = relativedelta(ret_date, birth_date)
        st.info(f"גיל בפרישה: {rdiff.years}.{rdiff.months}")

    # --- ניהול קופות (מנגנון חסין לשגיאות Key) ---
    st.subheader("💰 ריכוז קופות וצבירות")
    
    if 'funds' not in st.session_state or not isinstance(st.session_state.funds, list):
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
    processed_funds = []

    for i, fund in enumerate(st.session_state.funds):
        # הגנה מפני KeyError במידה וה-session_state ישן
        current_name = fund.get('name', '')
        current_type = fund.get('type', 'קצבתי')
        current_amount = fund.get('amount', 0.0)
        current_coeff = fund.get('coeff', 200.0)

        with st.expander(f"קופה {i+1}: {current_name}", expanded=True):
            c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
            
            new_name = c1.text_input("שם הקופה", value=current_name, key=f"n_{i}")
            new_type = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if current_type == 'קצבתי' else 1, key=f"t_{i}")
            new_amount = c3.number_input("צבירה (₪)", value=float(current_amount), key=f"a_{i}")
            
            if new_type == 'קצבתי':
                new_coeff = c4.number_input("מקדם ידני", value=float(current_coeff), step=0.01, key=f"c_{i}")
                pension = new_amount / new_coeff if new_coeff > 0 else 0
                total_pension += pension
                st.write(f"קצבה חזויה: **₪{pension:,.2f}**")
            else:
                new_coeff = current_coeff
                total_capital += new_amount
                c4.write(""); c4.caption("ללא מקדם")

            processed_funds.append({'name': new_name, 'type': new_type, 'amount': new_amount, 'coeff': new_coeff})

    st.session_state.funds = processed_funds

    # --- סיכום והורדת דוח ---
    st.divider()
    st.subheader(f"📊 סיכום דוח פרישה - {emp_name}")
    
    r1, r2, r3 = st.columns(3)
    r1.metric("קצבה חודשית ברוטו", f"₪{total_pension:,.2f}")
    r2.metric("הון חד פעמי", f"₪{total_capital:,.0f}")
    r3.metric("סה\"כ נכסים", f"₪{(total_capital + sum(f['amount'] for f in processed_funds if f['type']=='קצבתי')):,.0f}")

    # ייצוא פשוט ל-CSV (שאפשר לפתוח באקסל)
    if st.button("📥 הורד נתונים לאקסל (CSV)"):
        df = pd.DataFrame(processed_funds)
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("לחץ להורדה", data=csv, file_name=f"pension_report_{emp_name}.csv", mime="text/csv")

if __name__ == "__main__":
    main()
