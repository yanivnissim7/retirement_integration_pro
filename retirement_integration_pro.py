import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- נתוני יסוד ומדדי עתיד ---
KITZBA_MAX = 9430 # תקרת קצבה מזכה בסיס
STAGES = {
    2026: {"pct": 0.575, "label": "57.5% (נוכחי)"},
    2027: {"pct": 0.625, "label": "62.5% (שלב ג')"},
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
    st.set_page_config(page_title="אפקט - תחזית פרישה 2028", layout="wide")
    st.markdown("""<style>.main { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 נתוני בסיס")
        client_name = st.text_input("שם הלקוח", value="")
        ret_date = st.date_input("תאריך פרישה", value=date(2026, 3, 1))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=35.0)
        
        st.divider()
        st.header("💰 מענקים (טופס 161)")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=500000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("מענקים פטורים ב-15 שנה", value=0)

    # --- חישוב פטור 161 ונוסחת נסיגה ---
    exempt_limit = min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT)
    total_exempt_grant = min(total_grant_bruto, seniority * exempt_limit)
    taxable_grant = total_grant_bruto - total_exempt_grant
    
    seniority_factor = 32 / seniority if seniority > 32 else 1.0
    reduction_val = (total_exempt_grant + past_exempt_grants) * 1.35 * seniority_factor

    st.markdown(f"<h1>תכנון פרישה אסטרטגי - אפקט</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💰 ריכוז קופות", "📑 קיבוע זכויות", "🔄 דוח פריסה", "📊 כדאיות ותחזית 2028"])

    with tab1:
        st.subheader("ריכוז קצבאות")
        v_pension = st.number_input("קצבה ותיקה/תקציבית חודשית:", value=0)
        
        if 'funds' not in st.session_state:
            st.session_state.funds = [{'name': 'קופה 1', 'type': 'קצבתי', 'amount': 1000000.0, 'coeff': 197.10, 'include': True}]
        
        total_pension_val = v_pension
        for i, fund in enumerate(st.session_state.funds):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 1])
            fund['amount'] = c3.number_input("צבירה ₪", value=float(fund.get('amount',0)), key=f"a_{i}")
            if fund['type'] == 'קצבתי':
                fund['coeff'] = c4.number_input("מקדם", value=float(fund.get('coeff',200)), key=f"c_{i}")
                total_pension_val += fund['amount'] / fund['coeff']

    with tab2:
        st.subheader("קיבוע זכויות - ניצול סל הפטור (2026)")
        sal_ptur_2026 = (KITZBA_MAX * STAGES[2026]["pct"]) * 180
        rem_sal_2026 = max(0, sal_ptur_2026 - reduction_val)
        
        pct_to_pension = st.select_slider("אחוז לטובת הקצבה:", options=range(0,101,10), value=100)
        current_mon_exemp = (rem_sal_2026 / 180) * (pct_to_pension / 100)
        
        st.info(f"יתרת סל פטור נוכחית (2026): {fmt_num(rem_sal_2026)}")
        st.metric("פטור חודשי כיום", fmt_num(current_mon_exemp))

    with tab3:
        st.subheader("דוח פריסה")
        num_years = st.slider("שנות פריסה:", 1, 6, 6)
        ann_tax_grant = taxable_grant / num_years
        rows = []
        for i in range(num_years):
            yr = ret_date.year + i
            # חישוב מס לפי פטור שמתעדכן עם השנים (סימולציה)
            current_yr_pct = STAGES.get(yr, STAGES[2028])["pct"]
            yr_sal_ptur = (KITZBA_MAX * current_yr_pct) * 180
            yr_rem_sal = max(0, yr_sal_ptur - reduction_val)
            yr_mon_exemp = (yr_rem_sal / 180) * (pct_to_pension / 100)
            
            total_bruto = (total_pension_val * 12) + ann_tax_grant
            tax_t, m_r = calculate_income_tax(max(0, (total_bruto/12) - yr_mon_exemp), credit_points)
            
            rows.append({"שנה": yr, "ברוטו שנתי": fmt_num(total_bruto), "פטור חודשי בשנה זו": fmt_num(yr_mon_exemp), "מדרגה": f"{m_r*100:.0f}%"})
        st.table(pd.DataFrame(rows))

    with tab4:
        st.subheader("📈 תחזית גידול בפטור ובנטו (2026-2028)")
        
        forecast_data = []
        for yr in [2026, 2027, 2028]:
            yr_pct = STAGES[yr]["pct"]
            yr_sal_ptur = (KITZBA_MAX * yr_pct) * 180
            yr_rem_sal = max(0, yr_sal_ptur - reduction_val)
            yr_mon_exemp = (yr_rem_sal / 180) * (pct_to_pension / 100)
            
            tax_no_ex, _ = calculate_income_tax(total_pension_val, credit_points)
            tax_with_ex, _ = calculate_income_tax(max(0, total_pension_val - yr_mon_exemp), credit_points)
            saving = tax_no_ex - tax_with_ex
            
            forecast_data.append({"שנה": yr, "סל פטור כולל": yr_sal_ptur, "פטור חודשי": yr_mon_exemp, "חיסכון חודשי בנטו": saving})

        df_f = pd.DataFrame(forecast_data)
        
        # גרף גידול בחיסכון החודשי
        fig_future = go.Figure()
        fig_future.add_trace(go.Bar(x=df_f['שנה'], y=df_f['חיסכון חודשי בנטו'], marker_color='#3498db', text=df_f['חיסכון חודשי בנטו'].apply(fmt_num), textposition='auto'))
        fig_future.update_layout(title="גידול בחיסכון המס החודשי (נטו בכיס)", yaxis_title="₪")
        st.plotly_chart(fig_future, use_container_width=True)
        
        st.write(f"ℹ️ **שים לב:** בשנת 2028, בזכות העלייה ל-67% פטור, הפטור החודשי שלך יגדל ל-**{fmt_num(df_f.iloc[2]['פטור חודשי'])}**, מה שיוסיף לך עוד נטו בכל חודש.")

if __name__ == "__main__":
    main()
