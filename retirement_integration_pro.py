import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- מנוע מקדמים דינמי ללא הגבלת גיל קשיחה ---
def calculate_flexible_coeff(gender, exact_age, guarantee, spouse_birth, emp_birth, survivor_pct, retro_months):
    # בסיס מקדמים לפי נספח ו' ו-ח'
    # המנוע מחשב את המרחק מגיל היעד (67 לגבר, 64 לאישה) ומתאים את המקדם
    if gender == 'גבר':
        # גיל 67 בסיס 181.49. כל שנה פחות = +3.45 למקדם. כל שנה יותר = -3.2 למקדם.
        base = 181.49 + (67 - exact_age) * 3.45
    else:
        # גיל 64 בסיס 200.82.
        base = 200.82 + (64 - exact_age) * 3.7
    
    # תוספת תקופת הבטחה (לפי לוחות הפניקס)
    guarantee_map = {0: 0, 60: 0.48, 120: 2.06, 180: 5.07, 240: 10.16}
    coeff = base + guarantee_map.get(guarantee, 0)
    
    # חישוב פער גילאים מדויק מול בן/ת הזוג
    age_diff = (emp_birth - spouse_birth).days / 365.25
    
    # התאמת נספח ח' - פער גילאים (כל שנת פער מעבר ל-3 שנים מוסיפה למקדם)
    if age_diff > 3:
        coeff += (age_diff - 3) * 0.142
    elif age_diff < -3:
        coeff -= (abs(age_diff) - 3) * 0.11
        
    # התאמת שיעור שאירים (בסיס 60%)
    coeff += (survivor_pct - 60) * 0.155
    
    # חודשי רטרו (0-3)
    coeff *= (1 + (retro_months * 0.00185))
    
    return max(coeff, 100.0) # הגנת מינימום למקדם

def main():
    st.set_page_config(page_title="אפקט - סימולטור פרישה ללא מגבלה", layout="wide")
    st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)
    
    st.title("🏆 סימולטור פרישה מקצועי - אפקט")
    st.write("מנוע חישוב גמיש - תמיכה בכל טווח גילאי הפרישה")

    with st.sidebar:
        st.header("👤 נתוני העמית")
        emp_birth = st.date_input("תאריך לידה עמית", value=datetime(1960, 5, 15), 
                                 min_value=datetime(1930, 1, 1), max_value=datetime(2010, 1, 1))
        gender = st.selectbox("מין", ["גבר", "אישה"])
        
        st.divider()
        st.header("📅 מועד פרישה")
        # הרחבת הטווח לחיפוש חופשי
        ret_date = st.date_input("תאריך פרישה מבוקש", value=datetime(2027, 8, 1))
        
        # חישוב גיל מדויק במועד הפרישה (שנים וחודשים)
        rdiff = relativedelta(ret_date, emp_birth)
        exact_age = rdiff.years + (rdiff.months / 12)
        
        st.success(f"גיל פרישה מדויק: {rdiff.years} שנים ו-{rdiff.months} חודשים")
        
        st.divider()
        st.header("👫 בן/ת זוג ושאירים")
        spouse_birth = st.date_input("תאריך לידה בן/ת זוג", value=datetime(1964, 1, 1),
                                    min_value=datetime(1930, 1, 1), max_value=datetime(2020, 1, 1))
        survivor_pct = st.select_slider("אחוז קצבה לשאיר", options=[30, 40, 50, 60, 75, 100], value=60)
        
        st.divider()
        st.header("⚙️ הגדרות נוספות")
        guarantee = st.selectbox("תקופת הבטחה (חודשים)", [0, 60, 120, 180, 240], index=4)
        retro_months = st.selectbox("חודשי רטרו", [0, 1, 2, 3], index=0)

    # חישוב המקדם ללא חסימות גיל
    final_coeff = calculate_flexible_coeff(gender, exact_age, guarantee, spouse_birth, emp_birth, survivor_pct, retro_months)
    
    # תצוגת תוצאות
    st.subheader("📊 ניתוח פרישה מותאם אישית")
    assets = st.number_input("צבירה פנסיונית כוללת (₪)", value=1000000.0, step=10000.0)
    pension = assets / final_coeff

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("מקדם משוקלל", f"{final_coeff:.2f}")
    with c2:
        st.metric("קצבה חודשית (ברוטו)", f"₪{pension:,.0f}")
    with c3:
        # חישוב גיל נוכחי להצגה
        age_now = relativedelta(datetime.now().date(), emp_birth)
        st.metric("גיל הלקוח היום", f"{age_now.years}.{age_now.months}")

    st.write("---")
    # טבלת פירוט להדפסה
    details = {
        "פרמטר": ["גיל פרישה מדויק", "פער גילאים מבן/ת זוג", "שיעור שאירים", "חודשי רטרו", "תקופת הבטחה"],
        "ערך": [f"{rdiff.years}.{rdiff.months}", f"{(emp_birth - spouse_birth).days/365.25:.1f} שנים", f"{survivor_pct}%", f"{retro_months}", f"{guarantee} חודשים"]
    }
    st.table(pd.DataFrame(details))

if __name__ == "__main__":
    main()
