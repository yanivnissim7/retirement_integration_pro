import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- נתוני יסוד 2026 ---
SAL_PTUR_MAX = 976005 
MAX_WAGE_FOR_EXEMPT = 13750 

def fmt_num(num): return f"{float(num):,.0f}"

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
    st.set_page_config(page_title="מערכת פרישה פרו - אפקט", layout="wide")

    # RTL CSS
    st.markdown("""
        <style>
        .main, .stTabs, div[data-testid="stMetricValue"], .stMarkdown, p, h1, h2, h3, label {
            direction: rtl; text-align: right !important;
        }
        .stTable { direction: rtl; }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 פרטי דוח")
        agent_name = st.text_input("סוכן מטפל", value="ישראל ישראלי")
        client_name = st.text_input("שם הלקוח")
        client_id = st.text_input("ת.ז")
        retirement_date = st.date_input("תאריך פרישה", value=datetime(2025, 12, 31))
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        
        st.divider()
        st.header("💰 מענקים (פיצויים)")
        total_grant_bruto = st.number_input("סך מענק ברוטו", value=0)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        seniority = st.number_input("שנות ותק", value=1.0)
        past_exempt_grants = st.number_input("פטורים שנוצלו בעבר", value=0)

    st.markdown(f"""
        <div style="text-align: right; background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-right: 5px solid #007bff;">
            <h1 style="margin:0;">מערכת ניהול פרישה אינטגרטיבית - אפקט</h1>
            <p>לקוח: {client_name if client_name else "---"} | סוכן: {agent_name}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- שלב א': ריכוז קופות ---
    st.subheader("📋 ריכוז קופות וצבירות")
    
    if 'rows' not in st.session_state:
        st.session_state.rows = [{'קופה': 'קרן פנסיה', 'קצבתי': 1000000.0, 'הוני': 0.0, 'מקדם': 200.0}]

    def add_row(): st.session_state.rows.append({'קופה': '', 'קצבתי': 0.0, 'הוני': 0.0, 'מקדם': 1.0})
    
    edited_df = st.data_editor(pd.DataFrame(st.session_state.rows), num_rows="dynamic", use_container_width=True)
    
    # חישוב קצבה נגזרת מהטבלה
    edited_df['קצבה חזויה'] = edited_df.apply(lambda row: row['קצבתי'] / row['מקדם'] if row['מקדם'] > 0 else 0, axis=1)
    
    total_pension_from_table = edited_df['קצבה חזויה'].sum()
    total_honi_from_table = edited_df['הוני'].sum()

    col1, col2 = st.columns(2)
    col1.metric("סה''כ קצבה חזויה (ברוטו)", f"₪{fmt_num(total_pension_from_table)}")
    col2.metric("סה''כ צבירה הונית", f"₪{fmt_num(total_honi_from_table)}")

    # --- חישובי מס וקיבוע (מבוסס על הטבלה) ---
    expected_pension = total_pension_from_table
    
    actual_exempt_now = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant_for_spread = total_grant_bruto - actual_exempt_now
    seniority_ratio = 32 / seniority if seniority > 32 else 1
    reduction = ((actual_exempt_now + past_exempt_grants) * 1.35) * seniority_ratio
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction)
    max_mon_exemp = rem_sal_base / 180

    st.divider()
    st.subheader("2. אופטימיזציה של סל הפטור")
    pct_to_pension = st.select_slider("ניצול פטור לטובת הקצבה (היתרה להון):", options=range(0, 101, 10), value=0)
    selected_mon_exemp = max_mon_exemp * (pct_to_pension / 100)
    
    tab1, tab2 = st.tabs(["📊 ניתוח קצבה ונטו", "🔄 פריסת מענקים"])

    with tab1:
        tax_no_ex, _ = calculate_income_tax(expected_pension, credit_points)
        tax_with_ex, _ = calculate_income_tax(max(0, expected_pension - selected_mon_exemp), credit_points)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("קצבה נטו", f"₪{fmt_num(expected_pension - tax_with_ex)}", f"+₪{fmt_num(tax_no_ex - tax_with_ex)}")
        c2.metric("מס חודשי", f"₪{fmt_num(tax_with_ex)}")
        c3.metric("פטור הוני שנותר", f"₪{fmt_num(rem_sal_base * (1 - pct_to_pension/100))}")

    with tab2:
        st.write("### סימולציית פריסה")
        is_after_oct = retirement_date.month >= 10
        start_year = st.selectbox("שנת תחילת פריסה:", [retirement_date.year, retirement_date.year + 1], index=1 if is_after_oct else 0)
        num_years = st.slider("שנות פריסה:", 1, 6, 6)
        
        ann_grant = taxable_grant_for_spread / num_years
        spread_rows = []
        total_tax_spread = 0
        
        for i in range(num_years):
            yr = start_year + i
            p_m = 12 if (yr != retirement_date.year) else (12 - retirement_date.month)
            t_p, _ = calculate_income_tax(max(0, expected_pension - selected_mon_exemp), credit_points)
            t_total, m_rate = calculate_income_tax(max(0, expected_pension + (ann_grant/12) - selected_mon_exemp), credit_points)
            tax_on_g = (t_total - t_p) * 12
            total_tax_spread += tax_on_g
            spread_rows.append({"שנה": yr, "ברוטו שנתי": (expected_pension * p_m) + ann_grant, "מס": t_total * 12, "מדרגה": f"{m_rate*100:.0f}%"})
        
        st.table(pd.DataFrame(spread_rows))
        st.success(f"חיסכון מוערך בפריסה: ₪{fmt_num((taxable_grant_for_spread * 0.47) - total_tax_spread)}")

if __name__ == "__main__":
    main()
