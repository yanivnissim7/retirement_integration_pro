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
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]
    if 'v_pension' not in st.session_state: st.session_state.v_pension = 0.0

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 נתוני לקוח")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 1, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0, step=0.1)
        st.divider()
        st.header("💰 מענקים (161)")
        total_grant_bruto = st.number_input("סך מענקים ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע", value=13750)
        past_exempt_grants = st.number_input("פטורים ב-15 שנה", value=0)
        st.divider()
        work_income_retirement_year = st.number_input("הכנסת עבודה בשנת הפרישה (ברוטו)", value=150000)

    # --- מנוע חישוב ---
    actual_exempt_161 = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant = total_grant_bruto - actual_exempt_161
    s_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_val = (actual_exempt_161 + past_exempt_grants) * 1.35 * s_factor

    tab1, tab2, tab3, tab4 = st.tabs(["💰 קופות וצבירה", "📑 קיבוע זכויות", "🔄 דוח פריסה למס הכנסה", "📊 ניתוח כדאיות כלכלית"])

    # --- טאב 1: קופות וצבירה ---
    with tab1:
        st.subheader("ריכוז קופות וצבירות")
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
        res1, res2, res3 = st.columns(3)
        res1.metric("סך הון הוני (מזומן)", fmt_num(sum_honi_total))
        res2.metric("קצבה חודשית ברוטו", fmt_num(pension_total))
        res3.metric("מענק פטור (161)", fmt_num(actual_exempt_161))

    # --- טאב 2: קיבוע זכויות ---
    with tab2:
        st.subheader("קיבוע זכויות - ניצול סל פטור")
        pct_to_pension = st.select_slider("אחוז הפטור לקצבה (היתרה להון)", options=range(0,101,10), value=100)
        
        # חישוב 2026 ו-2028
        sal_26 = max(0, (KITZBA_MAX * 0.575 * 180) - reduction_val)
        sal_28 = max(0, (KITZBA_MAX * 0.670 * 180) - reduction_val)
        
        mon_ex_26 = (sal_26 / 180) * (pct_to_pension / 100)
        honi_ex_26 = sal_26 * (1 - (pct_to_pension / 100))
        
        mon_ex_28 = (sal_28 / 180) * (pct_to_pension / 100)
        honi_ex_28 = sal_28 * (1 - (pct_to_pension / 100))

        st.write(f"🔍 מקדם נסיגה: **{1.35*s_factor:.3f}**")
        c26, c28 = st.columns(2)
        with c26:
            st.info("### שנת 2026")
            st.write(f"פטור חודשי: **{fmt_num(mon_ex_26)}**")
            st.write(f"הון פטור מקצבה: **{fmt_num(honi_ex_26)}**")
        with c28:
            st.success("### שנת 2028")
            st.write(f"פטור חודשי: **{fmt_num(mon_ex_28)}**")
            st.write(f"הון פטור מקצבה: **{fmt_num(honi_ex_28)}**")

    # --- טאב 3: דוח פריסה ---
    with tab3:
        st.subheader("דוח עזר למס הכנסה - פריסת מענקים")
        start_spread = st.radio("תזמון פריסה:", ["שנת הפרישה", "שנה לאחר הפרישה"], horizontal=True)
        s_year = ret_date.year if start_spread == "שנת הפרישה" else ret_date.year + 1
        
        ann_grant = taxable_grant / 6
        rows = []
        total_tax_spread = 0
        for i in range(6):
            yr = s_year + i
            # הכנסה בשנה הראשונה כוללת את השכר שנצבר עד הפרישה
            inc_other = work_income_retirement_year if yr == ret_date.year else 0
            inc_pension = (pension_for_spread * 12) if yr >= ret_date.year else 0
            
            total_inc_no_grant = inc_other + inc_pension
            total_with_grant = total_inc_no_grant + ann_grant
            
            # מס
            tax_full, _ = calculate_income_tax(total_with_grant/12, credit_points)
            tax_base, _ = calculate_income_tax(total_inc_no_grant/12, credit_points)
            tax_on_grant = (tax_full - tax_base) * 12
            total_tax_spread += tax_on_grant

            rows.append({
                "שנה": yr,
                "הכנסה מעבודה": fmt_num(inc_other),
                "הכנסה מקצבה": fmt_num(inc_pension),
                "פריסת מענק חייב": fmt_num(ann_grant),
                "סה\"כ הכנסה שנתית": fmt_num(total_with_grant),
                "מס שנתי על המענק": fmt_num(max(0, tax_on_grant))
            })
        
        st.table(pd.DataFrame(rows))
        
        tax_no_spread = taxable_grant * 0.47 # לפי מדרגה מקסימלית
        saving = tax_no_spread - total_tax_spread
        st.success(f"סך חיסכון במס בביצוע פריסה: **{fmt_num(saving)}**")
        
        if work_income_retirement_year > (pension_for_spread * 12):
            st.warning("💡 המלצה: כדאי לשקול פריסה שנה לאחר הפרישה כדי להימנע ממיסוי גבוה בשנה בה היו הכנסות עבודה.")

    # --- טאב 4: כדאיות כלכלית ---
    with tab4:
        st.subheader("ניתוח כדאיות: הון פטור מול חיסכון מס 15 שנה")
        
        def get_roi(rem_sal, p_total):
            mon_ex = rem_sal / 180
            t_no, _ = calculate_income_tax(p_total, credit_points)
            t_yes, _ = calculate_income_tax(max(0, p_total - mon_ex), credit_points)
            return (t_no - t_yes) * 180

        roi_26 = get_roi(sal_26, pension_total)
        roi_28 = get_roi(sal_28, pension_total)

        c_a, c_b = st.columns(2)
        with c_a:
            st.write("#### השוואה 2026")
            f1 = go.Figure(data=[
                go.Bar(name='לקיחת הון פטור', x=['2026'], y=[sal_26], marker_color='#2ecc71', text=fmt_num(sal_26), textposition='auto'),
                go.Bar(name='חיסכון מס 15 שנה', x=['2026'], y=[roi_26], marker_color='#3498db', text=fmt_num(roi_26), textposition='auto')
            ])
            st.plotly_chart(f1)
        with c_b:
            st.write("#### השוואה 2028")
            f2 = go.Figure(data=[
                go.Bar(name='לקיחת הון פטור', x=['2028'], y=[sal_28], marker_color='#27ae60', text=fmt_num(sal_28), textposition='auto'),
                go.Bar(name='חיסכון מס 15 שנה', x=['2028'], y=[roi_28], marker_color='#2980b9', text=fmt_num(roi_28), textposition='auto')
            ])
            st.plotly_chart(f2)

if __name__ == "__main__":
    main()
