import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- נתוני יסוד ומדדי עתיד (תיקון 190) ---
KITZBA_MAX = 9430 
STAGES = {
    2026: {"pct": 0.575, "label": "57.5%"},
    2027: {"pct": 0.625, "label": "62.5%"},
    2028: {"pct": 0.670, "label": "67%"}
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
    st.set_page_config(page_title="אפקט - מערכת תכנון פרישה אסטרטגית", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; } div[data-testid="stMetricValue"] { color: #1f77b4; font-size: 1.5rem; }</style>""", unsafe_allow_html=True)

    # --- Sidebar: נתוני בסיס ו-161 ---
    with st.sidebar:
        st.header("👤 פרטי לקוח")
        client_name = st.text_input("שם הלקוח", value="")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 1, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0)
        
        st.divider()
        st.header("💰 נתוני מענקים (161)")
        total_grant_bruto = st.number_input("סך מענקי פרישה ברוטו", value=600000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("מענקים פטורים ב-15 שנה", value=0)

    # חישוב 161 וקיזוז (נוסחת נסיגה)
    exempt_limit = min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT)
    total_exempt_grant = min(total_grant_bruto, seniority * exempt_limit)
    taxable_grant = total_grant_bruto - total_exempt_grant
    
    # נוסחת הנסיגה עם התייחסות לוותק מעל 32
    seniority_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_val = (total_exempt_grant + past_exempt_grants) * 1.35 * seniority_factor
    
    st.markdown(f"<h1>אפקט - תכנון פרישה כולל</h1>", unsafe_allow_html=True)

    tab_funds, tab_fix, tab_spread, tab_roi = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "🔄 דוח פריסה", "📊 כדאיות ותחזית"])

    # --- טאב 1: ריכוז קופות ---
    with tab_funds:
        st.subheader("פירוט צבירות וקצבאות")
        v_pension = st.number_input("קצבה חודשית קיימת (ותיקה/תקציבית) ₪", value=0)
        
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'name': 'מנורה מבטחים', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]
        
        if st.button("➕ הוסף קופה/פוליסה"):
            st.session_state.funds.append({'name': '', 'type': 'קצבתי', 'amount': 0.0, 'coeff': 200.0, 'include': True})
            st.rerun()

        sum_honi = 0.0
        sum_kitzbati_capital = 0.0
        sum_expected_pension = v_pension
        pension_for_spread = v_pension

        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1, 1])
            fund['name'] = c1.text_input(f"שם קופה {i+1}", fund.get('name',''), key=f"n_{i}")
            fund['type'] = c2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund.get('amount',0)), key=f"a_{i}")
            
            if fund['type'] == "הוני":
                sum_honi += fund['amount']
                c4.write(""); c5.write("")
            else:
                sum_kitzbati_capital += fund['amount']
                fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
                p_val = fund['amount'] / fund['coeff'] if fund['coeff'] > 0 else 0
                sum_expected_pension += p_val
                fund['include'] = c5.checkbox("בפריסה?", value=fund.get('include', True), key=f"inc_{i}")
                if fund['include']:
                    pension_for_spread += p_val

        st.divider()
        res_c1, res_c2, res_c3 = st.columns(3)
        res_c1.metric("סה\"כ הון (מזומן)", fmt_num(sum_honi))
        res_c2.metric("צבירה לקצבה", fmt_num(sum_kitzbati_capital))
        res_c3.metric("סה\"כ קצבה חודשית ברוטו", fmt_num(sum_expected_pension))

    # --- טאב 2: קיבוע זכויות ---
    with tab_fix:
        st.subheader("חישוב סל הפטור (תיקון 190)")
        sal_ptur_2026 = (KITZBA_MAX * STAGES[2026]["pct"]) * 180
        rem_sal_2026 = max(0, sal_ptur_2026 - reduction_val)
        
        st.write(f"תקרת סל הפטור 2026: **{fmt_num(sal_ptur_2026)}**")
        st.write(f"קיזוז מענקים (לאחר מקדם ותק {seniority_factor:.2f}): **{fmt_num(reduction_val)}**")
        st.success(f"יתרת הון פטורה לניצול: **{fmt_num(rem_sal_2026)}**")
        
        pct_to_pension = st.select_slider("חלוקת הסל (הון מול קצבה):", options=range(0,101,10), value=50)
        selected_mon_exemp = (rem_sal_2026 / 180) * (pct_to_pension / 100)
        rem_honi_ptur = rem_sal_2026 * (1 - (pct_to_pension / 100))
        
        k_c1, k_c2 = st.columns(2)
        k_c1.metric("פטור חודשי על הקצבה", fmt_num(selected_mon_exemp))
        k_c2.metric("הון פטור למשיכה מידית", fmt_num(rem_honi_ptur))

    # --- טאב 3: דוח פריסה ---
    with tab_spread:
        st.subheader("פריסת מס על המענק החייב")
        st.info(f"מענק פטור (161): {fmt_num(total_exempt_grant)} | מענק חייב: {fmt_num(taxable_grant)}")
        
        start_year = st.selectbox("תחילת פריסה:", [ret_date.year, ret_date.year + 1])
        num_years = st.slider("מספר שנות פריסה:", 1, 6, 6)
        work_inc_first_year = st.number_input("הכנסות עבודה בשנה הראשונה (ברוטו):", value=0)
        
        ann_tax_grant = taxable_grant / num_years
        total_tax_spread = 0
        rows = []
        
        # חישוב יחסי לשנה ראשונה (לפי חודשים שנותרו)
        months_left = 12 - ret_date.month + 1
        
        for i in range(num_years):
            yr = start_year + i
            # עדכון פטור לפי שנת המס (2027/2028)
            yr_pct = STAGES.get(yr, STAGES[2028])["pct"]
            yr_mon_exemp = (max(0, (KITZBA_MAX * yr_pct * 180) - reduction_val) / 180) * (pct_to_pension / 100)
            
            pension_ann = (pension_for_spread * (months_left if i==0 and yr==ret_date.year else 12))
            work_ann = work_inc_first_year if (i==0 and yr==ret_date.year) else 0
            
            total_bruto = pension_ann + work_ann + ann_tax_grant
            
            tax_total, m_r = calculate_income_tax(max(0, (total_bruto/12) - yr_mon_exemp), credit_points)
            tax_base, _ = calculate_income_tax(max(0, ((pension_ann + work_ann)/12) - yr_mon_exemp), credit_points)
            tax_on_grant = (tax_total - tax_base) * 12
            total_tax_spread += tax_on_grant

            rows.append({
                "שנה": yr,
                "קצבה שנתית": fmt_num(pension_ann),
                "שכר/הכנסות": fmt_num(work_ann),
                "מענק בפריסה": fmt_num(ann_tax_grant),
                "סה\"כ ברוטו": fmt_num(total_bruto),
                "מס על המענק": fmt_num(max(0, tax_on_grant)),
                "מדרגה": f"{m_r*100:.0f}%"
            })
            
        st.table(pd.DataFrame(rows))
        tax_no_spread = taxable_grant * 0.47
        st.success(f"חיסכון במס מהפריסה: {fmt_num(tax_no_spread - total_tax_spread)}")

    # --- טאב 4: כדאיות ---
    with tab_roi:
        st.subheader("ניתוח כדאיות: הון מזומן מול חיסכון מס מצטבר")
        
        forecast = []
        for yr in [2026, 2027, 2028]:
            yr_mon_exemp = (max(0, (KITZBA_MAX * STAGES[yr]["pct"] * 180) - reduction_val) / 180) * (pct_to_pension / 100)
            tax_raw, _ = calculate_income_tax(sum_expected_pension, credit_points)
            tax_with_ex, _ = calculate_income_tax(max(0, sum_expected_pension - yr_mon_exemp), credit_points)
            forecast.append({"שנה": yr, "חיסכון חודשי": tax_raw - tax_with_ex})

        df_f = pd.DataFrame(forecast)
        
        # חישוב 15 שנה מצטבר (הערכה הכוללת את עליית הפטור)
        total_15y_roi = (df_f.iloc[0]['חיסכון חודשי'] * 12) + (df_f.iloc[1]['חיסכון חודשי'] * 12) + (df_f.iloc[2]['חיסכון חודשי'] * 156)

        c_roi1, c_roi2 = st.columns(2)
        c_roi1.metric("הון פטור היום (לפי הסליידר)", fmt_num(rem_honi_ptur))
        c_roi2.metric("חיסכון מס מצטבר (15 שנה)", fmt_num(total_15y_roi))

        fig = go.Figure(data=[
            go.Bar(name='הון מזומן פטור', x=['השוואה'], y=[rem_honi_ptur], marker_color='#2ecc71', text=fmt_num(rem_honi_ptur), textposition='auto'),
            go.Bar(name='חיסכון מס (15 שנה)', x=['השוואה'], y=[total_15y_roi], marker_color='#3498db', text=fmt_num(total_15y_roi), textposition='auto')
        ])
        st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"📊 **תחזית חיסכון בנטו:** ב-2026 תחסוך {fmt_num(df_f.iloc[0]['חיסכון חודשי'])} לחודש. ב-2028 החיסכון יגדל ל-{fmt_num(df_f.iloc[2]['חיסכון חודשי'])} לחודש.")

    st.divider()
    st.markdown("<p style='text-align:center; color:gray; font-size:0.8em;'>אפקט סוכנות לביטוח | 2026</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
