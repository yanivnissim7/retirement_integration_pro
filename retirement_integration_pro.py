import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים משודרג (הפניקס 2024) ---
def get_advanced_coefficient(gender, age, guarantee, spouse_gender, age_diff, is_retro):
    # כאן מוטמעת הלוגיקה מנספח ו' כולל התאמות רטרו והפרשי גילאים
    # לצורך הדוגמה, נשתמש בבסיס הטבלה שהעלית עם התאמות קלות
    base_tables = {
        'גבר': {
            67: {240: 191.65, 180: 186.56, 120: 183.55, 60: 181.97, 0: 181.49},
            65: {240: 199.31, 180: 193.63, 120: 190.28, 60: 188.51, 0: 187.97}
        },
        'אישה': {
            67: {240: 198.53, 180: 194.30, 120: 192.12, 60: 191.07, 0: 190.75},
            62: {240: 219.38, 180: 213.26, 120: 210.00, 60: 208.52, 0: 208.06}
        }
    }
    
    # שליפת מקדם בסיס (אם הגיל לא קיים, לוקח את הכי קרוב)
    closest_age = min(base_tables[gender].keys(), key=lambda x: abs(x - age))
    coeff = base_tables[gender][closest_age].get(guarantee, 200.0)
    
    # התאמת רטרו (בדרך כלל מוסיף למקדם כ-0.5% עד 1% תלוי בתקופת הרטרו)
    if is_retro:
        coeff *= 1.005 
        
    # התאמת הפרש גילאים (לפי לוחות התקנון - כאן סימולציה של ההשפעה)
    # ככל שבן הזוג צעיר יותר, המקדם עולה
    if age_diff > 0: # בן הזוג צעיר יותר
        coeff += (age_diff * 0.15)
        
    return coeff

def main():
    st.set_page_config(page_title="אפקט - תכנון פרישה מתקדם", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🎯 סימולטור פרישה מקצועי - אפקט")
    st.info("חישוב דינמי לפי נתוני עמית ומוטבים - תקנון הפניקס 2024")

    # --- SIDEBAR מורחב ---
    with st.sidebar:
        st.header("👤 פרטי העמית")
        gender = st.selectbox("מין העמית", ["גבר", "אישה"])
        birth_date = st.date_input("תאריך לידה עמית", value=datetime(1959, 2, 21))
        ret_date = st.date_input("תאריך פרישה מתוכנן", value=datetime(2026, 8, 1))
        
        # חישוב גיל מדויק בפרישה
        diff = relativedelta(ret_date, birth_date)
        age_at_ret = diff.years + (diff.months / 12)
        st.write(f"**גיל בפרישה:** {age_at_ret:.2f}")

        st.divider()
        st.header("👫 פרטי בן/ת זוג")
        has_spouse = st.checkbox("יש בן/ת זוג", value=True)
        if has_spouse:
            spouse_gender = "אישה" if gender == "גבר" else "גבר"
            spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1962, 5, 10))
            age_diff = (birth_date - spouse_birth).days / 365.25 # הפרש בשנים
            st.write(f"הפרש גילאים: {age_diff:.1f} שנים")
        else:
            age_diff = 0
            spouse_gender = None

        st.divider()
        st.header("📋 הגדרות נוספות")
        guarantee = st.selectbox("תקופת הבטחה", [0, 60, 120, 180, 240], index=4)
        is_retro = st.checkbox("בקשה לרטרו (תשלום רטרואקטיבי)")
        credit_points = st.number_input("נקודות זיכוי", 2.25)

    # חישוב המקדם המשוכלל
    final_coeff = get_advanced_coefficient(gender, int(age_at_ret), guarantee, spouse_gender, age_diff, is_retro)

    # --- תצוגת תוצאות ---
    st.subheader("📊 דוח ריכוז מקדמים וקצבה")
    
    total_assets = st.number_input("יתרה צבורה כוללת (₪)", value=1289354.0)
    pension_bruto = total_assets / final_coeff

    c1, c2, c3 = st.columns(3)
    c1.metric("מקדם משוקלל", f"{final_coeff:.2f}")
    c2.metric("קצבה ברוטו", f"₪{pension_bruto:,.0f}")
    c3.metric("סטטוס רטרו", "כן" if is_retro else "לא")

    st.write("---")
    tab1, tab2 = st.tabs(["📝 פירוט מקצועי", "🔄 סימולציית מס"])
    
    with tab1:
        st.write(f"**ניתוח עבור:** {gender} בפרישה בגיל {age_at_ret:.1f}")
        if has_spouse:
            st.write(f"**כיסוי שאירים:** כולל בן/ת זוג ({spouse_gender})")
        st.write(f"**תקופת הב
