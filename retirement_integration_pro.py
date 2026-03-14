import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- מנוע אקטוארי "אפקט" - גרסה 27.0 חסינה ---
def calculate_precise_menora_2026(gender, birth_date, ret_date, spouse_birth, req_guarantee, survivor_pct, mgt_fees, retro_months):
    # 1. חישוב גיל מדויק
    rdiff = relativedelta(ret_date, birth_date)
    exact_age = rdiff.years + (rdiff.months / 12) + (rdiff.days / 365.25)
    
    # 2. טבלת עוגן נספח א' (גבר) - מורחבת
    # הערה: המקדמים מתחת ל-60 ומעל 70 מחושבים לפי אינטרפולציה/ריגרסיה
    anchors_base = {
        60: 214.98, 61: 210.42, 62: 207.10, 63: 203.67, 64: 200.13,
        65: 196.45, 66: 191.01, 67: 187.08, 68: 183.04, 69: 178.88, 70: 174.58
    }
    
    # מנגנון שליפת בסיס חסין לכל גיל (18-90)
    if exact_age < 60:
        # עליה של כ-4.5 נקודות לכל שנה מתחת ל-60
        base = 214.98 + (60 - exact_age) * 4.5
    elif exact_age <= 70:
        floor_age = int(exact_age)
        ceil_age = floor_age + 1
        if floor_age in anchors_base and ceil_age in anchors_base:
            base = anchors_base[floor_age] - (anchors_base[floor_age] - anchors_base[ceil_age]) * (exact_age - floor_age)
        else:
            base = anchors_base.get(floor_age, 174.58)
    else:
        # ריגרסיה מעל גיל 70 (ירידה של 4.2 נקודות לשנה)
        base = 174.58 - (exact_age - 70) * 4.2

    # 3. תוספת הבטחה (נספח ד') - מנגנון קיזוז גיל 87
    max_guarantee_age = 87
    available_months = max(0, (max_guarantee_age - exact_age) * 12)
    eff_guarantee = min(float(req_guarantee), available_months)
    
    # חישוב עלות הבטחה בסיסית (יחסית לגיל)
    # גיל 60: 4.80 | גיל 70: 21.85
    if exact_age >= 70:
        base_guarantee_add = 21.85
    elif exact_age >= 60:
        base_guarantee_add = 4.80 + (21.85 - 4.80) * (exact_age - 60) / 10
    else:
        base_guarantee_add = 4.80 # עלות מינימלית לגילאים צעירים
    
    guarantee_impact = base_guarantee_add * (eff_guarantee / 240)
    
    # 4. שקלול סופי
    coeff = base + guarantee_impact
    coeff += (survivor_pct - 60) * 0.18 # תוספת שאיר
    
    # פער גילאים (מעל 3 שנים)
    age_diff = (birth_date - spouse_birth).days / 365.25
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.22
        
    # דמי ניהול ורטרו
    coeff /= (1 - (mgt_fees / 100))
    coeff *= (1 + (retro_months * 0.00355))
    
    return round(coeff, 2), round(eff_guarantee, 1), round(exact_age, 2)

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה", layout="wide")
    st.title("🏆 סימולטור פרישה אפקט - דיוק מלא")

    with st.sidebar:
        st.header("👤 נתוני העמית")
        gender = st.selectbox("מין", ["גבר", "אישה"])
        
        # טווח תאריכי לידה המאפשר גילאי 18-90
        min_date = date.today() - relativedelta(years=90)
        max_date = date.today() - relativedelta(years=18)
        
        birth_date = st.date_input("תאריך לידה עמית", 
                                   value=date(1965, 11, 26),
                                   min_value=min_date, 
                                   max_value=max_date)
        
        ret_date = st.date_input("תאריך פרישה (תחילת קצבה)", value=date(2026, 11, 26))
        
        st.divider()
        st.header("👫 נתוני בן/ת זוג")
        # טווח גילאים לבן/ת זוג (18-90)
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", 
                                     value=date(1968, 11, 26),
                                     min_value=min_date, 
                                     max_value=date.today() - relativedelta(years=18))
        
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ מסלול פרישה")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        mgt_fees = st.number_input("דמי ניהול מהקצבה (%)", value=0.3, step=0.1)
        retro = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=0)

    # הרצת המנוע
    res_coeff, eff_g, exact_age = calculate_precise_menora_2026(
        gender, birth_date, ret_date, spouse_birth, guarantee, survivor_pct, mgt_fees, retro
    )

    # תצוגת תוצאות
    st.subheader(f"ניתוח אקטוארי - גיל פרישה {exact_age}")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.metric("הבטחה אפקטיבית (עד גיל 87)", f"{eff_g} חודשים")
        st.info(f"החישוב מבוסס על גיל פרישה מדויק של {exact_age} שנים.")

    with col2:
        st.markdown(f"""
            <div style="background-color:#f9f9f9; padding:20px; border-radius:15px; border:2px solid #1e88e5; text-align:center;">
                <h3 style="margin:0; color:#1e88e5;">מקדם סופי</h3>
                <h1 style="margin:10px; font-size:48px;">{res_coeff}</h1>
            </div>
        """, unsafe_allow_html=True)

    # טבלת צבירות
    st.divider()
    st.subheader("💰 ריכוז קופות וצבירות")
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מבטחים', 'amount': 1000000.0}]

    for i, fund in enumerate(st.session_state.funds):
        c1, c2, c3 = st.columns([3, 2, 2])
        fund['name'] = c1.text_input("שם הקופה", fund['name'], key=f"n_{i}")
        fund['amount'] = c2.number_input("סכום הצבירה (₪)", fund['amount'], key=f"a_{i}")
        pension = fund['amount'] / res_coeff if res_coeff > 0 else 0
        c3.markdown(f"**קצבה צפויה:** ₪{pension:,.0f}")

if __name__ == "__main__":
    main()
