import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי "אפקט" - כיול מנורה/הפניקס 2025 ---
def calculate_pension_coeff_pro(gender, exact_age, req_guarantee, survivor_pct, age_diff, retro_months, mgt_fees):
    # 1. טבלאות עוגן - נספח א' (גבר) מעודכן
    # שים לב: המקדמים יורדים עם הגיל בגלל תוחלת חיים קצרה יותר בפרישה מאוחרת
    anchors_male = {
        60: 214.98, 61: 210.42, 62: 207.10, 63: 203.67, 64: 200.13,
        65: 196.45, 66: 191.01, 67: 187.08, 68: 183.04, 69: 178.88, 70: 174.58
    }
    
    # 2. ריגרסיה מעבר לגיל 70
    if exact_age <= 70:
        age_floor = int(exact_age)
        age_ceil = age_floor + 1
        base = anchors_male[age_floor] - (anchors_male[age_floor] - anchors_male[age_ceil]) * (exact_age - age_floor)
    else:
        # ריגרסיה מתונה יותר מעבר ל-70 כדי לא "להפיל" את המקדם מהר מדי
        base = 174.58 - ((exact_age - 70) * 3.8)

    # 3. מנגנון הבטחה עד גיל 87 - הכיול הקריטי
    # בגיל 70, כל חודש הבטחה "יקר" יותר לקרן מאשר בגיל 60.
    max_guarantee_age = 87
    available_months = max(0, (max_guarantee_age - exact_age) * 12)
    eff_guarantee = min(float(req_guarantee), available_months)
    
    # כיול תוספת הבטחה: בגיל 70, 240 חודשים (או היתרה עד 87) מוסיפים כ-18-20 נקודות למקדם
    guarantee_factor = 0.085 # פקטור מוגדל לסנכרון עם הפניקס
    guarantee_impact = eff_guarantee * guarantee_factor
    
    coeff = base + guarantee_impact
    
    # 4. התאמת שאירים (מעבר ל-60% בסיס)
    coeff += (survivor_pct - 60) * 0.22
    
    # 5. פער גילאים (נספח ח')
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.25
    
    # 6. רטרו ודמי ניהול
    coeff *= (1 + (retro_months * 0.00355))
    coeff *= (1 / (1 - (mgt_fees / 100)))
    
    return round(coeff, 2), round(eff_guarantee, 1)

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה", layout="wide")
    
    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה", value=date(1956, 11, 30))
        ret_date = st.date_input("תאריך פרישה", value=date.today())
        
        st.header("⚙️ מסלול")
        req_guarantee = st.selectbox("הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        survivor_pct = st.select_slider("שאיר %", options=[30, 60, 100], value=60)
        mgt_fees = st.number_input("דמי ניהול %", value=0.3)

        rdiff = relativedelta(ret_date, emp_birth)
        exact_age = rdiff.years + (rdiff.months / 12)
        
        target_coeff, eff_g = calculate_pension_coeff_pro(
            "גבר", exact_age, req_guarantee, survivor_pct, 4.0, 0, mgt_fees
        )

        st.divider()
        st.write(f"גיל פרישה: {rdiff.years}.{rdiff.months}")
        st.write(f"הבטחה אפקטיבית: {eff_g}")
        st.success(f"מקדם סופי: {target_coeff}")

    # טבלה וסיכום (קוצר לצורך התצוגה)
    st.subheader("💰 ריכוז קופות")
    amount = st.number_input("צבירה קצבתית", value=1000000)
    st.info(f"קצבה צפויה: ₪{amount / target_coeff:,.0f}")

if __name__ == "__main__":
    main()
