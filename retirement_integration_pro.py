import streamlit as st
import pandas as pd
from datetime import datetime

# --- מנוע מקדמים מורחב לפי נספח ו' (הפניקס 2024) ---
def get_coefficient_from_table(gender, age, guarantee):
    # נתונים שחולצו משני הצילומים שהעלית (טבלה 1 המלאה)
    tables = {
        'גבר': {
            67: {0: 181.49, 60: 181.97, 120: 183.55, 180: 186.56, 240: 191.65},
            66: {0: 184.69, 60: 185.19, 120: 186.86, 180: 190.04, 240: 195.42},
            65: {0: 187.97, 60: 188.51, 120: 190.28, 180: 193.63, 240: 199.31},
            64: {0: 191.35, 60: 191.93, 120: 193.81, 180: 197.35, 240: 203.35},
            63: {0: 194.84, 60: 195.46, 120: 197.46, 180: 201.21, 240: 207.54},
            62: {0: 198.44, 60: 199.11, 120: 201.23, 180: 205.21, 240: 211.89},
            61: {0: 202.16, 60: 202.87, 120: 205.13, 180: 209.35, 240: 216.42},
            60: {0: 206.01, 60: 206.77, 120: 209.16, 180: 213.66, 240: 221.14}
        },
        'אישה': {
            67: {0: 190.75, 60: 191.07, 120: 192.12, 180: 194.30, 240: 198.53},
            66: {0: 194.02, 60: 194.35, 120: 195.47, 180: 197.83, 240: 202.39},
            65: {0: 197.37, 60: 197.74, 120: 198.93, 180: 201.49, 240: 206.40},
            64: {0: 200.82, 60: 201.22, 120: 202.49, 180: 205.27, 240: 210.56},
            63: {0: 204.38, 60: 204.81, 120: 206.18, 180: 209.19, 240: 214.88},
            62: {0: 208.06, 60: 208.52, 120: 210.00, 180: 213.26, 240: 219.38},
            61: {0: 211.85, 60: 212.35, 120: 213.95, 180: 217.48, 240: 224.06},
            60: {0: 215.77, 60: 216.31, 120: 218.05, 180: 221.87, 240: 228.94}
        }
    }
    return tables.get(gender, {}).get(age, {}).get(guarantee, 200.0)

def calculate_neto(bruto, credit_points):
    # מדרגות מס 2026 (משוערות/מעודכנות)
    brackets = [(7010, 0.10), (10060, 0.14), (16150, 0.20), (22440, 0.31), (46690, 0.35), (float('inf'), 0.47)]
    tax, prev = 0, 0
    for limit, rate in brackets:
        if bruto > prev:
            taxable = min(bruto, limit) - prev
            tax += taxable * rate
            prev = limit
        else: break
    return max(0, tax - (credit_points * 250))

def main():
    st.set_page_config(page_title="אפקט - מערכת פרישה אינטגרטיבית", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🎯 סימולטור פרישה - אפקט")
    st.info("המערכת מעודכנת עם כל נתוני נספח ו' (גברים ונשים) - יולי 2024")

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("👤 פרטי לקוח")
        gender = st.selectbox("מין העמית", ["גבר", "אישה"])
        age_at_ret = st.slider("גיל פרישה", 60, 67, 67)
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        credit_points = st.number_input("נקודות זיכוי", 2.25)
        st.divider()
        st.header("💰 צבירה")
        total_assets = st.number_input("יתרה צבורה לקצבה (₪)", value=1289354.0, step=1000.0)

    # שליפת המקדם מהמנוע הפנימי
    coeff = get_coefficient_from_table(gender, age_at_ret, guarantee)
    pension_bruto = total_assets / coeff
    tax = calculate_neto(pension_bruto, credit_points)

    # --- תצוגת דוח ---
    st.subheader("📋 סיכום נתונים")
    col1, col2, col3 = st.columns(3)
    col1.metric("מקדם המרה", f"{coeff:.2f}")
    col2.metric("קצבה חודשית ברוטו", f"₪{pension_bruto:,.0f}")
    col3.metric("קצבה נטו (משוער)", f"₪{pension_bruto - tax:,.0f}")

    st.write("---")
    
    # טאבים למחשבונים נוספים
    tab1, tab2 = st.tabs(["📊 נוסחת הנסיגה (סל הפטור)", "🔄 פריסת פיצויים"])
    
    with tab1:
        st.subheader("מחשבון סל פטור (הון פטור נותר)")
        grant_now = st.number_input("פיצויים פטורים שנמשכו כעת", value=0)
        grant_past = st.number_input("פיצויים פטורים שנמשכו ב-15 שנה אחרונות", value=0)
        
        # חישוב בסיסי של נוסחת הנסיגה (לפי 2026)
        total_exemption_bucket = 976005 # תקרה מוערכת
        reduction = (grant_now + grant_past) * 1.35
        rem_bucket = max(0, total_exemption_bucket - reduction)
        
        st.write(f"**יתרת סל הפטור להיוון או קצבה:** ₪{rem_bucket:,.0f}")
        st.caption("החישוב מתבסס על מכפיל 1.35 לפי הוראות סעיף 9א.")

if __name__ == "__main__":
    main()
