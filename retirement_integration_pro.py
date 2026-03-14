import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי "אפקט" - מנורה 2025 (גברים ונשים) ---
def calculate_menora_pension_coeff(gender, exact_age, requested_guarantee, survivor_pct, age_diff, retro_months, mgt_fees):
    # 1. טבלאות עוגנים (לפי נספחים א' וב' ששלחת)
    anchors_male = {
        60: 214.98, 61: 210.42, 62: 207.10, 63: 203.67, 64: 200.13,
        65: 196.45, 66: 191.01, 67: 187.08, 68: 183.04, 69: 178.88, 70: 174.58
    }
    
    anchors_female = {
        60: 225.40, 61: 221.15, 62: 216.85, 63: 212.50, 64: 208.10,
        65: 203.65, 66: 199.15, 67: 194.60, 68: 189.95, 69: 185.25, 70: 180.50
    }
    
    selected_anchors = anchors_male if gender == "גבר" else anchors_female
    
    # 2. מנגנון ריגרסיה (השלמת הטבלה מעבר לגיל 70)
    if exact_age <= 70:
        age_floor = int(exact_age)
        age_ceil = age_floor + 1
        if age_floor in selected_anchors and age_ceil in selected_anchors:
            base = selected_anchors[age_floor] - (selected_anchors[age_floor] - selected_anchors[age_ceil]) * (exact_age - age_floor)
        else:
            base = selected_anchors.get(age_floor, 174.58 if gender == "גבר" else 180.50)
    else:
        # ריגרסיה מעבר לגיל 70: ירידה שנתית ממוצעת
        factor = 4.2 if gender == "גבר" else 4.5
        extra_years = exact_age - 70
        base = selected_anchors[70] - (extra_years * factor)

    # 3. מנגנון קיזוז הבטחה חכם - עד גיל 87 לכל המאוחר
    # החישוב: כמה חודשים נותרו מהגיל הנוכחי ועד גיל 87
    max_guarantee_age = 87 
    available_months_until_87 = max(0, (max_guarantee_age - exact_age) * 12)
    
    # ההבטחה בפועל היא המינימום בין מה שביקש לבין מה שנותר עד גיל 87
    effective_guarantee = min(float(requested_guarantee), available_months_until_87)
    
    # תוספת למקדם בגין הבטחה (כ-0.02 נקודות לכל חודש הבטחה אפקטיבי)
    guarantee_impact = (effective_guarantee / 240) * 4.85
    coeff = base + guarantee_impact
    
    # 4. נספח ח' (פער גילאים) - אם בת הזוג צעירה ב-3 שנים ומעלה
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.22
    
    # 5. התאמה לאחוז שאיר (בסיס 60%)
    coeff += (survivor_pct - 60) * 0.18
    
    # 6. רטרו (מכפיל אקטוארי על כל המקדם)
    coeff *= (1 + (retro_months * 0.00355))
    
    # 7. דמי ניהול (מגדילים את המקדם)
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return round(coeff, 2), round(effective_guarantee, 1)

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה - אפקט")
    st.caption("מותאם למנורה 2025 | כולל ריגרסיה ומגבלת הבטחה לגיל 87")

    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=date(1956, 11, 30))
        gender = st.selectbox("מין", ["גבר", "אישה"])
        ret_date = st.date_input("תאריך פרישה", value=date.today())
        
        st.divider()
        st.header("👫 בן/ת זוג")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=date(1960, 1, 1))
        survivor_pct = st.select_slider("אחוז לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ הגדרות מסלול")
        req_guarantee = st.selectbox("הבטחה מבוקשת (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=0)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)

        # חישובים
        rdiff = relativedelta(ret_date, emp_birth)
        exact_age_ret = rdiff.years + (rdiff.months / 12)
        age_diff_val = (emp_birth - spouse_birth).days / 365.25
        
        target_coeff, eff_g = calculate_menora_pension_coeff(
            gender, exact_age_ret, req_guarantee, survivor_pct, age_diff_val, retro_months, mgt_fees
        )

        st.divider()
        st.subheader("📊 ניתוח אקטוארי")
        st.write(f"**גיל פרישה:** {rdiff.years}.{rdiff.months}")
        
        if eff_g < req_guarantee:
            st.warning(f"הבטחה הוגבלה ל-{eff_g} חודשים (תקרת גיל 87)")
        else:
            st.info(f"הבטחה אפקטיבית: {eff_g} חודשים")
            
        st.success(f"**מקדם סופי:** {target_coeff:.2f}")

    # --- טבלת כספים ---
    st.subheader("💰 ריכוז קופות וצבירות")
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מקיפה', 'type': 'קצבתי', 'amount': 1000000.0}]

    for i, fund in enumerate(st.session_state.funds):
        col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
        fund['name'] = col1.text_input("תיאור", fund['name'], key=f"n_{i}")
        fund['type'] = col2.selectbox("סוג", ["קצבתי", "הוני"], key=f"t_{i}")
        fund['amount'] = col3.number_input("סכום (₪)", fund['amount'], key=f"a_{i}")
        if fund['type'] == "קצבתי":
            col4.number_input("מקדם", value=target_coeff, key=f"c_{i}")
        else:
            col4.write(""); col4.caption("כסף הוני")

    total_pension = sum([f['amount']/target_coeff for f in st.session_state.funds if f['type']=="קצבתי"])
    total_capital = sum([f['amount'] for f in st.session_state.funds if f['type']=="הוני"])
    
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("קצבה חודשית ברוטו", f"₪{total_pension:,.0f}")
    c2.metric("סה\"כ הון חד פעמי", f"₪{total_capital:,.0f}")

if __name__ == "__main__":
    main()
