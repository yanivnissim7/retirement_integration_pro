import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

def main():
    st.set_page_config(page_title="אפקט - דוח פרישה מלא", layout="wide")
    st.title("🏆 מערכת 'אפקט' - תכנון פרישה אסטרטגי")

    # --- נתוני בסיס (גילאי 18-90) ---
    today = date.today()
    min_birth = today - relativedelta(years=90)
    max_birth = today - relativedelta(years=18)

    with st.sidebar:
        st.header("👤 פרטי לקוח")
        emp_name = st.text_input("שם מלא", "ישראל ישראלי")
        birth_date = st.date_input("תאריך לידה", value=date(1965, 11, 26), min_value=min_birth, max_value=max_birth)
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 11, 26))
        rdiff = relativedelta(ret_date, birth_date)
        st.info(f"גיל בפרישה: {rdiff.years}.{rdiff.months}")

    # --- חלק 1: ריכוז קופות וצבירות ---
    st.header("💰 1. ריכוז קופות וצבירות (הזנה ידנית)")
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10}]

    col_btns = st.columns([1, 1, 4])
    if col_btns[0].button("➕ הוסף קופה"):
        st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0})
        st.rerun()
    if col_btns[1].button("🗑️ נקה הכל"):
        st.session_state.funds = []
        st.rerun()

    total_pension = 0.0
    total_capital = 0.0
    
    # הצגת הקופות בטבלה ערוכה
    for i, fund in enumerate(st.session_state.funds):
        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
        fund['name'] = c1.text_input(f"שם קופה {i+1}", fund.get('name',''), key=f"n_{i}")
        fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if fund.get('type')=='קצבתי' else 1, key=f"t_{i}")
        fund['amount'] = c3.number_input("צבירה (₪)", value=float(fund.get('amount',0)), key=f"a_{i}")
        if fund['type'] == 'קצבתי':
            fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
            total_pension += fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
        else:
            total_capital += fund['amount']

    st.divider()

    # --- חלק 2: קיבוע זכויות (סל הפטור) ---
    st.header("📑 2. קיבוע זכויות - סל הפטור (161ד)")
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        grant_amount = st.number_input("מענקים פטורים שנתקבלו (15 שנה אחרונות)", value=0.0)
        pension_limit_2025 = 882648  # תקרת הפטור
    with col_k2:
        multiplier = 1.35
        consumed = grant_amount * multiplier
        remaining = max(0, pension_limit_2025 - consumed)
        st.metric("יתרת סל פטור להיוון/קצבה", f"₪{remaining:,.0f}")
        st.caption(f"ניצול סל: ₪{consumed:,.0f} מתוך ₪{pension_limit_2025:,.0f}")

    st.divider()

    # --- חלק 3: טבלת פריסה וכדאיות ---
    st.header("📉 3. פריסת מס וכדאיות כלכלית")
    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
        st.write("**טבלת פריסת מס (הערכה):**")
        spread_years = st.slider("שנות פריסה", 1, 6, 6)
        tax_data = []
        for y in range(1, spread_years + 1):
            tax_data.append({"שנה": f"שנה {y}", "הכנסה צפויה": f"₪{total_pension*12/spread_years:,.0f}", "מס משוער": "לפי מדרגות"})
        st.table(pd.DataFrame(tax_data))
    
    with col_p2:
        marginal_tax = st.number_input("מדרגת מס שולית (%)", value=20)
        if total_capital > 0:
            annuity_ratio = (total_pension * 12) / total_capital
            st.metric("תשואת קצבה שנתית (ROI)", f"{annuity_ratio:.2%}")

    st.divider()

    # --- חלק 4: סיכום והדפסה ---
    st.header("📋 4. סיכום דוח סופי")
    s1, s2, s3 = st.columns(3)
    s1.metric("קצבה חודשית ברוטו", f"₪{total_pension:,.2f}")
    s2.metric("סה\"כ הון חד פעמי", f"₪{total_capital:,.0f}")
    s3.metric("יתרת פטור בקיבוע", f"₪{remaining:,.0f}")

    # כפתור הדפסה בשיטת HTML
    report_html = f"""
    <div style="direction:rtl; text-align:right; font-family:Arial; padding:20px; border:1px solid #ccc;">
        <h2>דוח תכנון פרישה - אפקט</h2>
        <p><b>שם הלקוח:</b> {emp_name}</p>
        <p><b>גיל פרישה:</b> {rdiff.years}.{rdiff.months}</p>
        <hr>
        <h3>שורה תחתונה:</h3>
        <ul>
            <li>קצבה חודשית ברוטו: ₪{total_pension:,.2f}</li>
            <li>הון חד פעמי: ₪{total_capital:,.0f}</li>
            <li>יתרת סל פטור: ₪{remaining:,.0f}</li>
        </ul>
    </div>
    """
    
    if st.button("🖨️ הכן דוח להדפסה"):
        st.components.v1.html(report_html + "<script>window.print();</script>", height=400)

if __name__ == "__main__":
    main()
