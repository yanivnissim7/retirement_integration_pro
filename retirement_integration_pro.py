import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- נתוני יסוד 2026 ---
SAL_PTUR_MAX = 976005 
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
    st.set_page_config(page_title="אפקט - תכנון פרישה אסטרטגי", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; } div[data-testid="stMetricValue"] { font-size: 1.8rem; }</style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח", value="")
        ret_date = st.date_input("תאריך פרישה", value=date(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=33.4)
        
        st.divider()
        st.header("💰 מענקים")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=968000)
        salary_for_exempt = st.number_input("שכר קובע לפטור (161)", value=13750)
        past_exempt_grants = st.number_input("מענקים פטורים בעבר (15 שנה)", value=0)

    # חישובי בסיס
    exempt_amount = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant = total_grant_bruto - exempt_amount
    reduction = ((exempt_amount + past_exempt_grants) * 1.35) * (32/seniority if seniority > 32 else 1)
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction)

    st.markdown(f"<h1>תכנון פרישה אסטרטגי - אפקט סוכנות לביטוח</h1>", unsafe_allow_html=True)

    # --- טאב 1: ריכוז קופות ---
    tab_funds, tab_fix, tab_spread, tab_roi = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "🔄 דוח פריסה", "📊 כדאיות"])

    with tab_funds:
        st.subheader("ריכוז צבירות ומקדמים")
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]

        if st.button("➕ הוסף קופה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        total_pension_to_spread = 0.0
        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 1])
            fund['name'] = c1.text_input(f"שם קופה {i+1}", fund.get('name',''), key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund.get('amount',0)), key=f"a_{i}")
            if fund['type'] == 'קצבתי':
                fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
                fund['include'] = c5.checkbox("כלול בפריסה?", value=fund.get('include', True), key=f"inc_{i}")
                if fund['include']:
                    total_pension_to_spread += fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
            else:
                c4.write(""); c5.write("")

    with tab_fix:
        st.subheader("קיבוע זכויות (161ד)")
        pct_to_pension = st.select_slider("אחוז מהפטור לקצבה:", options=range(0,101,10), value=0)
        selected_mon_exemp = (rem_sal_base / 180) * (pct_to_pension / 100)
        rem_honi_ptur = rem_sal_base * (1 - (pct_to_pension / 100))
        
        k1, k2 = st.columns(2)
        k1.metric("פטור חודשי על הקצבה", fmt_num(selected_mon_exemp))
        k2.metric("הון פטור שנותר", fmt_num(rem_honi_ptur))

    with tab_spread:
        st.subheader("דוח פריסת מס להגשה")
        
        # לוגיקת 1.10 ואיבוד שנה
        is_after_oct = ret_date.month >= 10
        start_year = st.selectbox("שנת תחילת פריסה:", [ret_date.year, ret_date.year + 1] if is_after_oct else [ret_date.year, ret_date.year + 1], 
                                 help="בחירה בשנה הבאה כאשר הפרישה לפני 1.10 תגרור איבוד שנת פריסה.")
        
        max_spread = 6
        if not is_after_oct and start_year > ret_date.year:
            st.warning("⚠️ בגלל פרישה לפני 1.10 ודחיית פריסה, ניתן לפרוס ל-5 שנים בלבד.")
            max_spread = 5
        
        num_years = st.slider("מספר שנות פריסה:", 1, max_spread, max_spread)
        
        # הכנסות עבודה שנה א' והכנסה צפויה
        first_year_work_income = st.number_input("הכנסות עבודה בפועל בשנה הראשונה (ברוטו שנתי מהמעסיק):", value=0)
        other_inc_monthly = st.number_input("הכנסה חודשית צפויה בשנים הבאות (שכר/פנסיה נוספת):", value=0)

        ann_taxable_part = taxable_grant / num_years
        spread_rows = []
        total_tax_spread = 0
        
        for i in range(num_years):
            yr = start_year + i
            # הכנסה בסיסית: בשנה א' זה הכנסת עבודה, בשאר זה שכר צפוי + קצבה (רק אם סומן 'כלול')
            if i == 0 and yr == ret_date.year:
                base_annual = first_year_work_income + (total_pension_to_spread * (12 - ret_date.month))
            else:
                base_annual = (total_pension_to_spread + other_inc_monthly) * 12
            
            total_combined_annual = base_annual + ann_taxable_part
            tax_total, m_rate = calculate_income_tax(max(0, (total_combined_annual/12) - selected_mon_exemp), credit_points)
            tax_on_grant_yr = (tax_total - calculate_income_tax(max(0, (base_annual/12) - selected_mon_exemp), credit_points)[0]) * 12
            total_tax_spread += max(0, tax_on_grant_yr)

            spread_rows.append({
                "שנה": yr,
                "הכנסה בסיסית (שכר/קצבה)": fmt_num(base_annual),
                "חלק מענק חייב": fmt_num(ann_taxable_part),
                "סך ברוטו שנתי לדו\"ח": fmt_num(total_combined_annual),
                "מס שנתי על המענק": fmt_num(max(0, tax_on_grant_yr)),
                "מדרגת מס": f"{m_rate*100:.0f}%"
            })

        st.table(pd.DataFrame(spread_rows))
        
        # חיסכון במיסוי
        tax_no_spread = taxable_grant * 0.47
        st.write("### 📉 סיכום חיסכון במיסוי")
        res1, res2, res3 = st.columns(3)
        res1.error(f"מס ללא פריסה (47%): {fmt_num(tax_no_spread)}")
        res2.warning(f"מס בפריסה: {fmt_num(total_tax_spread)}")
        res3.success(f"חיסכון נטו במיסוי: {fmt_num(tax_no_spread - total_tax_spread)}")

    with tab_roi:
        st.subheader("כדאיות כלכלית")
        saving_15y = (calculate_income_tax(total_pension_to_spread, credit_points)[0] - 
                      calculate_income_tax(max(0, total_pension_to_spread - (rem_sal_base/180)), credit_points)[0]) * 180
        fig = go.Figure(data=[
            go.Bar(name='הון פטור מידי', x=['השוואה'], y=[rem_honi_ptur], marker_color='#2ecc71'),
            go.Bar(name='חיסכון מס בקצבה (15 שנה)', x=['השוואה'], y=[saving_15y], marker_color='#3498db')
        ])
        st.plotly_chart(fig)

    # דיסקליימר
    st.divider()
    st.markdown("""
        <div style="font-size: 0.8em; color: gray; text-align: center; direction: rtl;">
            <b>דיסקליימר:</b> דוח זה מהווה סימולציה בלבד המבוססת על הנתונים שנמסרו על ידי הלקוח ואינו מהווה אישור רשמי מרשויות המס. 
            החישובים מבוססים על הערכות חבות מס ועל החוק הידוע במועד הפקת הדוח (2026). 
            אפקט סוכנות לביטוח ומי מטעמה אינם אחראים לכל החלטה שתתקבל על סמך נתונים אלו. 
            מומלץ להיוועץ ביועץ מס או רואה חשבון טרם הגשת הדוחות בפועל.
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
