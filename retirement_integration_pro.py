import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- פרמטרים חוקיים ---
KITZBA_MAX = 9430 
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
    st.set_page_config(page_title="אפקט - מערכת מומחה לפרישה", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; } div.stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }</style>""", unsafe_allow_html=True)

    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]
    if 'v_pension' not in st.session_state: st.session_state.v_pension = 0.0

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("📋 פרטי הדוח")
        agent_name = st.text_input("שם הסוכן / המתכנן", value="שם הסוכן שלך")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        st.divider()
        st.header("👤 נתוני בסיס")
        ret_date = st.date_input("תאריך פרישה", value=date(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0, step=0.1)
        st.divider()
        st.header("💰 מענקים והכנסות")
        total_grant_bruto = st.number_input("סך מענקים ברוטו (161)", value=968000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("פטורים ב-15 שנה אחרונות", value=0)
        work_inc_ret_year = st.number_input("הכנסת עבודה בשנת הפרישה (ברוטו)", value=150000)

    # --- מנוע חישוב מתוקן (נוסחת הנסיגה המדויקת) ---
    # הפטור למענק מוגבל לפי ותק X תקרה (או המענק עצמו, הנמוך מביניהם)
    actual_exempt_161 = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant = total_grant_bruto - actual_exempt_161
    
    # חישוב מקדם ותק לנסיגה (32 חלקי ותק אם הותק גדול מ-32)
    seniority_factor = 32 / seniority if seniority > 32 else 1.0
    
    # חישוב הנסיגה: (פטורים נוכחיים + עבר) * 1.35 * מקדם ותק
    reduction_val = (actual_exempt_161 + past_exempt_grants) * 1.35 * seniority_factor

    # --- כותרת ---
    st.markdown(f"<h1 style='text-align: center; color: #1E3A8A;'>דוח סיכום פרישה ל: {client_name}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'><b>נערך על ידי:</b> {agent_name} | <b>תאריך:</b> {date.today().strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💰 קופות וצבירה", "📑 קיבוע זכויות ונטו", "🔄 דוח פריסה", "📊 כדאיות כלכלית"])

    with tab1:
        st.subheader("ריכוז קופות וצבירות")
        st.session_state.v_pension = st.number_input("קצבה חודשית ותיקה/תקציבית", value=float(st.session_state.v_pension))
        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        pension_total = st.session_state.v_pension
        pension_for_spread = st.session_state.v_pension
        sum_honi_total = 0.0

        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1, 1])
            fund['type'] = c2.selectbox(f"סוג {i+1}", ["קצבתי", "הוני"], key=f"t_{i}")
            fund['amount'] = c3.number_input(f"צבירה {i+1}", value=float(fund['amount']), key=f"a_{i}")
            if fund['type'] == "קצבתי":
                fund['coeff'] = c4.number_input(f"מקדם {i+1}", value=float(fund['coeff']), key=f"c_{i}")
                p_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                pension_total += p_val
                fund['include'] = c5.checkbox(f"בפריסה? {i+1}", value=fund['include'], key=f"inc_{i}")
                if fund['include']: pension_for_spread += p_val
            else:
                sum_honi_total += fund['amount']
        
        st.divider()
        res1, res2, res3 = st.columns(3)
        res1.metric("סך הון הוני", fmt_num(sum_honi_total))
        res2.metric("קצבה חודשית ברוטו", fmt_num(pension_total))
        res3.metric("מענק פטור (161)", fmt_num(actual_exempt_161))

    with tab2:
        st.subheader("קיבוע זכויות - השפעה על הנטו")
        pct_to_pension = st.select_slider("אחוז ניצול פטור לקצבה", options=range(0,101,10), value=100)
        
        sal_26 = max(0, (KITZBA_MAX * 0.575 * 180) - reduction_val)
        sal_28 = max(0, (KITZBA_MAX * 0.670 * 180) - reduction_val)
        
        mon_ex_26 = (sal_26 / 180) * (pct_to_pension / 100)
        
        tax_no_ex, _ = calculate_income_tax(pension_total, credit_points)
        tax_with_ex_26, _ = calculate_income_tax(max(0, pension_total - mon_ex_26), credit_points)

        # תצוגת נוסחת הנסיגה המעודכנת למשתמש
        if seniority > 32:
             st.write(f"🔍 **נסיגה מהסל:** {fmt_num(reduction_val)} (מענק פטור {fmt_num(actual_exempt_161)} × 1.35 × 32/{seniority:.1f})")
        else:
             st.write(f"🔍 **נסיגה מהסל:** {fmt_num(reduction_val)} (מענק פטור {fmt_num(actual_exempt_161)} × 1.35)")
        
        c26, c28 = st.columns(2)
        with c26:
            st.info("### מצב ב-2026")
            st.metric("יתרת סל פטור", fmt_num(sal_26))
            st.metric("תוספת חודשית לנטו", fmt_num(tax_no_ex - tax_with_ex_26))
            st.metric("קצבת נטו סופית", fmt_num(pension_total - tax_with_ex_26))
        with c28:
            st.success("### פוטנציאל ב-2028")
            st.metric("יתרת סל פטור", fmt_num(sal_28))
            mon_ex_28 = (sal_28 / 180) * (pct_to_pension / 100)
            tax_with_ex_28, _ = calculate_income_tax(max(0, pension_total - mon_ex_28), credit_points)
            st.metric("תוספת חודשית לנטו", fmt_num(tax_no_ex - tax_with_ex_28))
            st.metric("קצבת נטו סופית", fmt_num(pension_total - tax_with_ex_28))

    with tab3:
        st.subheader("דוח עזר למס הכנסה - פריסת מענקים")
        ann_grant = taxable_grant / 6
        data_spread = []
        for i in range(6):
            yr = ret_date.year + i
            inc_work = work_inc_ret_year if yr == ret_date.year else 0
            inc_pension = (pension_for_spread * 12) if yr >= ret_date.year else 0
            tax_full, _ = calculate_income_tax((inc_work + inc_pension + ann_grant)/12, credit_points)
            tax_base, _ = calculate_income_tax((inc_work + inc_pension)/12, credit_points)
            tax_on_grant = (tax_full - tax_base) * 12
            data_spread.append([yr, fmt_num(inc_work), fmt_num(inc_pension), fmt_num(ann_grant), fmt_num(max(0, tax_on_grant))])
        
        st.table(pd.DataFrame(data_spread, columns=["שנה", "הכנסה מעבודה", "הכנסה מקצבה", "חלק יחסי מענק", "מס שנתי משוער"]))

    with tab4:
        st.subheader("כדאיות כלכלית: הון מול קצבה")
        roi_26 = (tax_no_ex - tax_with_ex_26) * 180
        f1 = go.Figure(data=[
            go.Bar(name='משיכת הון פטור', x=['2026'], y=[sal_26], marker_color='#2ecc71'),
            go.Bar(name='ערך פטור מקצבה (15 שנה)', x=['2026'], y=[roi_26], marker_color='#3498db')
        ])
        st.plotly_chart(f1)

    st.markdown("---")
    st.markdown("<div style='direction: rtl; text-align: right; font-size: 12px; color: gray;'>דיסקליימר: סימולציה בלבד. חבות המס הסופית תיקבע על ידי פקיד השומה.</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
