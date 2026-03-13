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
    st.set_page_config(page_title="דוח פרישה - אפקט סוכנות לביטוח", layout="wide")

    # CSS ליישור לימין (RTL) והתאמה להדפסה
    st.markdown("""
        <style>
        .main, .stTabs, div[data-testid="stMetricValue"], .stMarkdown, p, h1, h2, h3, label {
            direction: rtl;
            text-align: right !important;
        }
        .stTable { direction: rtl; }
        @media print {
            .stTabs [data-baseweb="tab-list"] { display: none; }
            .stTabs [data-baseweb="tab-panel"] { display: block !important; opacity: 1 !important; position: relative !important; }
            .stButton, .stSlider, .stSelectbox, [data-testid="stSidebar"], header { display: none !important; }
            .main { width: 100% !important; direction: rtl; }
            .print-footer { display: block !important; margin-top: 50px; border-top: 1px solid black; padding-top: 20px; direction: rtl; }
        }
        .print-footer { display: none; }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 פרטי לקוח וסוכן")
        agent_name = st.text_input("שם הסוכן המטפל", value="ישראל ישראלי")
        client_name = st.text_input("שם הלקוח", value="")
        client_id = st.text_input("מספר זהות", value="")
        
        st.divider()
        st.header("📋 נתוני פרישה")
        retirement_date = st.date_input("תאריך פרישה", value=datetime(2025, 12, 31))
        expected_pension = st.number_input("קצבת ברוטו חודשית", value=18400)
        credit_points = st.number_input("נקודות זיכוי", value=2.25)
        seniority = st.number_input("שנות ותק", value=33.4)
        
        st.divider()
        st.header("💰 מענקים")
        total_grant_bruto = st.number_input("סך מענק פרישה ברוטו", value=968000)
        salary_for_exempt = st.number_input("שכר קובע לפטור", value=13750)
        past_exempt_grants = st.number_input("סך מענקים פטורים בעבר", value=0)

    # כותרת הדוח המעודכנת
    st.markdown(f"""
        <div style="text-align: right; background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-right: 5px solid #007bff;">
            <h1 style="margin:0;">דוח תכנון פרישה אסטרטגי - אפקט סוכנות לביטוח בע"מ</h1>
            <p style="font-size: 1.2em; margin: 10px 0 0 0;">
                <b>עבור:</b> {client_name if client_name else "_______"} | <b>ת.ז:</b> {client_id if client_id else "_______"}
            </p>
            <p style="margin: 5px 0 0 0;"><b>סוכן מטפל:</b> {agent_name}</p>
        </div>
        <br>
    """, unsafe_allow_html=True)

    # --- חישובי ליבה ---
    actual_exempt_now = min(total_grant_bruto, seniority * min(salary_for_exempt, MAX_WAGE_FOR_EXEMPT))
    taxable_grant_for_spread = total_grant_bruto - actual_exempt_now
    seniority_ratio = 32 / seniority if seniority > 32 else 1
    reduction = ((actual_exempt_now + past_exempt_grants) * 1.35) * seniority_ratio
    rem_sal_base = max(0, SAL_PTUR_MAX - reduction)
    max_mon_exemp = rem_sal_base / 180

    st.subheader("1. אופטימיזציה של סל הפטור")
    pct_to_pension = st.select_slider("אחוז מהפטור לטובת הקצבה (השאר להון):", options=range(0, 101, 10), value=0)
    selected_mon_exemp = max_mon_exemp * (pct_to_pension / 100)
    rem_honi_ptur = rem_sal_base * (1 - (pct_to_pension / 100))

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📜 קיבוע וקצבה", "🔄 דוח פריסה והשוואה", "📊 כדאיות כלכלית"])

    with tab1:
        tax_no_ex, _ = calculate_income_tax(expected_pension, credit_points)
        tax_with_ex, _ = calculate_income_tax(max(0, expected_pension - selected_mon_exemp), credit_points)
        st.subheader("ניתוח השפעה על הקצבה וההון")
        c1, c2, c3 = st.columns(3)
        c1.metric("קצבה נטו (אחרי פטור)", f"₪{fmt_num(expected_pension - tax_with_ex)}", f"+₪{fmt_num(tax_no_ex - tax_with_ex)}")
        c2.metric("מס הכנסה חודשי", f"₪{fmt_num(tax_with_ex)}")
        c3.metric("סכום הוני פטור נותר", f"₪{fmt_num(rem_honi_ptur)}")

    with tab2:
        st.subheader("סימולציית פריסה מול תשלום מיידי")
        is_after_oct = retirement_date.month >= 10
        start_year = st.selectbox("שנת תחילת פריסה:", [retirement_date.year, retirement_date.year + 1], index=1 if is_after_oct else 0)
        
        max_years = 6
        if start_year > retirement_date.year and not is_after_oct:
            max_years = 5
            st.warning("שים לב: דחיית פריסה למי שפרש לפני 1.10 מקצרת את התקופה ל-5 שנים.")
            
        num_years = st.slider("שנות פריסה:", 1, max_years, max_years)
        ann_grant = taxable_grant_for_spread / num_years
        spread_rows = []
        total_tax_on_grant_only = 0
        
        for i in range(num_years):
            yr = start_year + i
            p_m = 12 if (yr != retirement_date.year) else (12 - retirement_date.month)
            p_ann = expected_pension * p_m
            tax_pension_only, _ = calculate_income_tax(max(0, (p_ann/12) - selected_mon_exemp), credit_points)
            tax_total_monthly, m_rate = calculate_income_tax(max(0, (p_ann/12) + (ann_grant/12) - selected_mon_exemp), credit_points)
            tax_on_grant_this_year = (tax_total_monthly - tax_pension_only) * 12
            total_tax_on_grant_only += tax_on_grant_this_year
            spread_rows.append({
                "שנה": yr, "ברוטו שנתי": p_ann + ann_grant, "מס שנתי כולל": tax_total_monthly * 12,
                "נטו שנתי": (p_ann + ann_grant) - (tax_total_monthly * 12), "מדרגת מס": f"{m_rate*100:.0f}%"
            })
        
        st.table(pd.DataFrame(spread_rows).style.format({c: "₪{:,.0f}" for c in ["ברוטו שנתי", "מס שנתי כולל", "נטו שנתי"]}))
        tax_no_spread_val = taxable_grant_for_spread * 0.47 
        st.write("### 📉 סיכום חיסכון במס על המענק:")
        col_a, col_b, col_c = st.columns(3)
        col_a.error(f"מס ללא פריסה: ₪{fmt_num(tax_no_spread_val)}")
        col_b.warning(f"מס בפריסה: ₪{fmt_num(total_tax_on_grant_only)}")
        col_c.success(f"חיסכון נקי: ₪{fmt_num(tax_no_spread_val - total_tax_on_grant_only)}")

    with tab3:
        st.subheader("כדאיות כלכלית: הון מול קצבה")
        tax_saving_15y = (tax_no_ex - calculate_income_tax(max(0, expected_pension - max_mon_exemp), credit_points)[0]) * 180
        fig = go.Figure(data=[
            go.Bar(name='הון נזיל פטור', x=['השוואה'], y=[rem_sal_base], marker_color='#2ecc71', text=f"₪{fmt_num(rem_sal_base)}", textposition='auto'),
            go.Bar(name='חיסכון מס בקצבה (15 שנה)', x=['השוואה'], y=[tax_saving_15y], marker_color='#3498db', text=f"₪{fmt_num(tax_saving_15y)}", textposition='auto')
        ])
        st.plotly_chart(fig, use_container_width=True)

    # חתימה משופרת להדפסה
    st.markdown(f"""
        <div class="print-footer">
            <table style="width:100%; border:none; direction: rtl;">
                <tr>
                    <td style="text-align:right;"><b>סוכן מטפל:</b> {agent_name}</td>
                    <td style="text-align:center;"><b>חתימת הלקוח ({client_name}):</b> _________________</td>
                    <td style="text-align:left;"><b>תאריך:</b> {datetime.now().strftime('%d/%m/%Y')}</td>
                </tr>
            </table>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()