import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- פרמטרים חוקיים ---
KITZBA_MAX = 9430 
STAGES = {
    2026: {"pct": 0.575, "label": "57.5%"},
    2027: {"pct": 0.625, "label": "62.5%"},
    2028: {"pct": 0.670, "label": "67% (יעד סופי)"}
}
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
    st.set_page_config(page_title="אפקט - תכנון פרישה אסטרטגי 2028", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    # --- SESSION STATE ---
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'קופה 1', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]
    if 'v_pension' not in st.session_state: st.session_state.v_pension = 0.0

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 נתוני לקוח")
        client_name = st.text_input("שם הלקוח", value="ישראל ישראלי")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 1, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0, step=0.1)
        
        st.divider()
        st.header("💰 מענקי פרישה (161)")
        total_grant_bruto = st.number_input("סך מענקים ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("פטורים ב-15 שנה", value=0)

    # --- מנוע חישוב ריאקטיבי (כולל ותק ו-2028) ---
    actual_exempt_161 = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant = total_grant_bruto - actual_exempt_161
    
    # נוסחת הנסיגה עם התייחסות לוותק > 32
    s_factor = 32 / seniority if seniority > 32 else 1.0
    eff_multiplier = 1.35 * s_factor
    reduction_val = (actual_exempt_161 + past_exempt_grants) * eff_multiplier

    # חישוב יתרות סל פטור לכל השלבים
    rem_sal_2026 = max(0, (KITZBA_MAX * STAGES[2026]["pct"] * 180) - reduction_val)
    rem_sal_2028 = max(0, (KITZBA_MAX * STAGES[2028]["pct"] * 180) - reduction_val)

    st.markdown(f"<h1>אפקט - אופטימיזציית פרישה (תיקון 190)</h1>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["💰 קופות וצבירה", "📑 קיבוע זכויות (2026-2028)", "🔄 דוח פריסה דינמי", "📊 ניתוח כדאיות מצטבר"])

    with tab1:
        st.subheader("ריכוז קצבאות")
        st.session_state.v_pension = st.number_input("קצבה חודשית ותיקה/תקציבית ₪", value=float(st.session_state.v_pension))
        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        sum_honi = 0.0
        pension_total = st.session_state.v_pension
        p_for_spread = st.session_state.v_pension

        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1, 1])
            fund['name'] = c1.text_input(f"שם {i+1}", fund['name'], key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], index=0 if fund['type']=="קצבתי" else 1, key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה", value=float(fund['amount']), key=f"a_{i}")
            if fund['type'] == "קצבתי":
                fund['coeff'] = c4.number_input("מקדם", value=float(fund['coeff']), key=f"c_{i}")
                p_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                pension_total += p_val
                fund['include'] = c5.checkbox("בפריסה?", value=fund['include'], key=f"inc_{i}")
                if fund['include']: p_for_spread += p_val
            else:
                sum_honi += fund['amount']
        
        st.metric("סה\"כ קצבה חודשית ברוטו (כולל הכל)", fmt_num(pension_total))

    with tab2:
        st.subheader("ניתוח פטור חודשי: היום מול 2028")
        st.write(f"ℹ️ **מקדם נסיגה אפקטיבי (ותק {seniority}):** {eff_multiplier:.3f}")
        
        pct_to_pension = st.select_slider("ניצול הפטור לקצבה (%):", options=range(0,101,10), value=100)
        
        mon_ex_26 = (rem_sal_2026 / 180) * (pct_to_pension / 100)
        mon_ex_28 = (rem_sal_2028 / 180) * (pct_to_pension / 100)
        
        tax_26, _ = calculate_income_tax(max(0, pension_total - mon_ex_26), credit_points)
        tax_28, _ = calculate_income_tax(max(0, pension_total - mon_ex_28), credit_points)

        c1, c2 = st.columns(2)
        with c1:
            st.info("**מצב נוכחי (2026)**")
            st.metric("פטור חודשי ממס", fmt_num(mon_ex_26))
            st.metric("קצבת נטו בכיס", fmt_num(pension_total - tax_26))
        with c2:
            st.success("**מצב עתידי (2028)**")
            st.metric("פטור חודשי ממס", fmt_num(mon_ex_28))
            st.metric("קצבת נטו בכיס", fmt_num(pension_total - tax_28))

    with tab3:
        st.subheader("דוח פריסה (מותאם לשינויי החקיקה 2026-2028)")
        ann_tax_grant = taxable_grant / 6
        rows = []
        for i in range(6):
            yr = ret_date.year + i
            # פטור שמתעדכן אוטומטית לפי שנת הפריסה
            curr_pct = STAGES.get(yr, STAGES[2028])["pct"]
            curr_mon_ex = (max(0, (KITZBA_MAX * curr_pct * 180) - reduction_val) / 180) * (pct_to_pension / 100)
            
            total_yr_bruto = (p_for_spread * 12) + ann_tax_grant
            tax_m, m_r = calculate_income_tax(max(0, (total_yr_bruto/12) - curr_mon_ex), credit_points)
            
            rows.append({
                "שנה": yr,
                "ברוטו שנתי": fmt_num(total_yr_bruto),
                "אחוז פטור חוקי": f"{curr_pct*100:.1f}%",
                "פטור חודשי בשנה זו": fmt_num(curr_mon_ex),
                "מדרגת מס": f"{m_r*100:.0f}%"
            })
        st.table(pd.DataFrame(rows))

    with tab4:
        st.subheader("📊 השוואת כדאיות: הון פטור מול חיסכון מס מצטבר (15 שנה)")
        
        # חיסכון 15 שנה הלוקח בחשבון את המעבר ל-2028
        tax_no, _ = calculate_income_tax(pension_total, credit_points)
        save_26_val = tax_no - tax_26
        save_28_val = tax_no - tax_28
        
        # חישוב מצטבר: שנתיים לפי 2026 + 13 שנה לפי 2028
        total_15y_saving = (save_26_val * 24) + (save_28_val * 156)

        c_roi1, c_roi2 = st.columns(2)
        c_roi1.metric("סכום הוני פטור (בבחירה של 0% לקצבה)", fmt_num(rem_sal_2028))
        c_roi2.metric("חיסכון מס מצטבר ב-15 שנה", fmt_num(total_15y_saving))

        fig = go.Figure(data=[
            go.Bar(name='הון פטור בסל 2028', x=['השוואה'], y=[rem_sal_2028], marker_color='#2ecc71', text=fmt_num(rem_sal_2028), textposition='auto'),
            go.Bar(name='חיסכון מס מצטבר (15 שנה)', x=['השוואה'], y=[total_15y_saving], marker_color='#3498db', text=fmt_num(total_15y_saving), textposition='auto')
        ])
        st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"💡 **בשורה התחתונה:** בזכות העלייה בפטור ב-2028, חיסכון המס המצטבר שלך ב-15 השנים הבאות צפוי להגיע ל-**{fmt_num(total_15y_saving)}**.")

if __name__ == "__main__":
    main()
