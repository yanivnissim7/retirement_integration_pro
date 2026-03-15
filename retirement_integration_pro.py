import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
from fpdf import FPDF

# --- הגדרות קבועות ---
KITZBA_MAX = 9430 
STAGES = {2026: 0.575, 2028: 0.670}
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

def main():
    st.set_page_config(page_title="אפקט - דוח סיכום פרישה", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; } div.stButton > button { width: 100%; }</style>""", unsafe_allow_html=True)

    # --- אתחול נתונים ---
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]
    if 'v_pension' not in st.session_state: st.session_state.v_pension = 0.0

    # --- SIDEBAR: מיתוג ופרטי בסיס ---
    with st.sidebar:
        st.header("📋 פרטי הדוח")
        agent_name = st.text_input("שם הסוכן / המתכנן", value="שם הסוכן שלך")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        st.divider()
        st.header("👤 נתוני בסיס")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 1, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0, step=0.1)
        st.divider()
        st.header("💰 מענקים והכנסות")
        total_grant_bruto = st.number_input("סך מענקים ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע", value=13750)
        past_exempt_grants = st.number_input("פטורים ב-15 שנה", value=0)
        work_inc_ret_year = st.number_input("הכנסת עבודה בשנת הפרישה", value=150000)

    # --- חישובים לוגיים מרכזיים ---
    actual_exempt_161 = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant = total_grant_bruto - actual_exempt_161
    s_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_val = (actual_exempt_161 + past_exempt_grants) * 1.35 * s_factor

    # --- כותרת הדוח ---
    st.markdown(f"<h1 style='text-align: center;'>דוח סיכום פרישה ל: {client_name}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>נערך על ידי: {agent_name} | תאריך: {date.today().strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💰 קופות וצבירה", "📑 קיבוע זכויות ונטו", "🔄 דוח פריסה", "📊 כדאיות כלכלית"])

    # --- טאב 1: קופות ---
    with tab1:
        st.session_state.v_pension = st.number_input("קצבה חודשית ותיקה/תקציבית", value=float(st.session_state.v_pension))
        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        sum_honi_total = 0.0
        pension_total = st.session_state.v_pension
        pension_for_spread = st.session_state.v_pension

        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1, 1])
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if fund['type']=="קצבתי" else 1, key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה", value=float(fund['amount']), key=f"a_{i}")
            if fund['type'] == "קצבתי":
                fund['coeff'] = c4.number_input("מקדם", value=float(fund['coeff']), key=f"c_{i}")
                p_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                pension_total += p_val
                fund['include'] = c5.checkbox("בפריסה?", value=fund['include'], key=f"inc_{i}")
                if fund['include']: pension_for_spread += p_val
            else:
                sum_honi_total += fund['amount']
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("סך מזומן הוני", fmt_num(sum_honi_total))
        m2.metric("קצבה חודשית ברוטו", fmt_num(pension_total))
        m3.metric("פטור במענק (161)", fmt_num(actual_exempt_161))

    # --- טאב 2: קיבוע זכויות ונטו ---
    with tab2:
        st.subheader("השפעת קיבוע הזכויות על הנטו החודשי")
        pct_to_pension = st.select_slider("ניצול הפטור לקצבה (%):", options=range(0,101,10), value=100)
        
        sal_26 = max(0, (KITZBA_MAX * 0.575 * 180) - reduction_val)
        sal_28 = max(0, (KITZBA_MAX * 0.670 * 180) - reduction_val)
        
        mon_ex_26 = (sal_26 / 180) * (pct_to_pension / 100)
        honi_ex_26 = sal_26 * (1 - (pct_to_pension / 100))
        
        tax_no_ex, _ = calculate_income_tax(pension_total, credit_points)
        tax_with_ex, _ = calculate_income_tax(max(0, pension_total - mon_ex_26), credit_points)

        st.info(f"ניתוח ל-2026: ללא קיבוע תשלם {fmt_num(tax_no_ex)} מס. עם הקיבוע תשלם {fmt_num(tax_with_ex)} מס.")
        
        n1, n2, n3 = st.columns(3)
        n1.metric("קצבת נטו (לפני קיבוע)", fmt_num(pension_total - tax_no_ex))
        n2.metric("קצבת נטו (אחרי קיבוע)", fmt_num(pension_total - tax_with_ex))
        n3.metric("תוספת לנטו כל חודש", fmt_num(tax_no_ex - tax_with_ex), delta_color="normal")

    # --- טאב 3: פריסה ---
    with tab3:
        st.subheader("דוח עזר למס הכנסה - פריסת מס")
        start_yr = st.radio("עיתוי:", ["שנת הפרישה", "שנה אחרי"], horizontal=True)
        s_year = ret_date.year if start_yr == "שנת הפרישה" else ret_date.year + 1
        
        ann_grant = taxable_grant / 6
        rows = []
        for i in range(6):
            yr = s_year + i
            inc_work = work_inc_ret_year if yr == ret_date.year else 0
            inc_pension = (pension_for_spread * 12) if yr >= ret_date.year else 0
            total_bruto = inc_work + inc_pension + ann_grant
            rows.append({"שנה": yr, "עבודה": fmt_num(inc_work), "קצבה": fmt_num(inc_pension), "מענק": fmt_num(ann_grant), "סה\"כ ברוטו": fmt_num(total_bruto)})
        st.table(pd.DataFrame(rows))

    # --- טאב 4: כדאיות ---
    with tab4:
        st.subheader("ניתוח כדאיות כלכלית 15 שנה")
        def get_roi(sal, p_total):
            m_ex = sal / 180
            t_no, _ = calculate_income_tax(p_total, credit_points)
            t_yes, _ = calculate_income_tax(max(0, p_total - m_ex), credit_points)
            return (t_no - t_yes) * 180
        
        roi_26 = get_roi(sal_26, pension_total)
        roi_28 = get_roi(sal_28, pension_total)

        col_a, col_b = st.columns(2)
        with col_a:
            st.write("#### שנת 2026")
            f1 = go.Figure(data=[go.Bar(name='הון פטור', x=['2026'], y=[sal_26], marker_color='#2ecc71'), go.Bar(name='חיסכון מס', x=['2026'], y=[roi_26], marker_color='#3498db')])
            st.plotly_chart(f1)
        with col_b:
            st.write("#### שנת 2028")
            f2 = go.Figure(data=[go.Bar(name='הון פטור', x=['2028'], y=[sal_28], marker_color='#27ae60'), go.Bar(name='חיסכון מס', x=['2028'], y=[roi_28], marker_color='#2980b9')])
            st.plotly_chart(f2)

    # --- ייצוא PDF (סימולציה) ---
    st.divider()
    if st.button("📥 ייצוא דוח מלא ל-PDF"):
        st.info("מייצר PDF... (בגרסת ה-Web יש להוריד את הקובץ שיפתח)")
        # כאן תבוא הלוגיקה של fpdf לשמירה
        st.write(f"הדוח עבור {client_name} מוכן להורדה.")

    # --- דיסקליימר ---
    st.markdown("---")
    st.markdown("""
    <div style='text-align: right; font-size: 12px; color: gray; direction: rtl;'>
    <b>דיסקליימר:</b> דוח זה מהווה סימולציה בלבד ואינו מהווה ייעוץ פנסיוני או ייעוץ מס מחליף. 
    הנתונים המופיעים בדוח מבוססים על המידע שנמסר על ידי המשתמש ועל הוראות החוק ותקנות מס הכנסה נכון למועד עריכת הדוח (כולל תיקון 190). 
    מומלץ לאמת את הנתונים הסופיים מול רשויות המס וקופות הגמל לפני ביצוע פעולות. 
    חבות המס הסופית תיקבע אך ורק על ידי פקיד השומה.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
