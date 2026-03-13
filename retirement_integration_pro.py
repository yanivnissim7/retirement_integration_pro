import streamlit as st
import pandas as pd
import os

# ניסיון לייבא ספריות חיצוניות עם הגנה
try:
    import openpyxl
    import plotly.graph_objects as go
except ImportError:
    st.error("השרת עדיין מתקין ספריות. המתן דקה ורענן את הדף (F5).")

def main():
    st.set_page_config(page_title="אפקט - מערכת פרישה", layout="wide")
    
    # בדיקה אם קובץ האקסל קיים בשרת
    excel_exists = os.path.exists('simulator_prisha.xlsm')
    
    if not excel_exists:
        st.warning("⚠️ קובץ האקסל 'simulator_prisha.xlsm' לא נמצא ב-GitHub. הסנכרון האוטומטי לא יפעל.")
    
    st.title("מערכת פרישה - אפקט")
    
    # טבלת קופות פשוטה להתחלה
    if 'rows' not in st.session_state:
        st.session_state.rows = [{'קופה': 'פנסיה', 'קצבתי': 1000000, 'הוני': 0, 'מקדם': 200}]
    
    df = pd.DataFrame(st.session_state.rows)
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    # כפתור סנכרון עם הגנה
    if st.button("🔄 נסה לסנכרן עם אקסל"):
        if not excel_exists:
            st.error("לא ניתן לסנכרן: הקובץ חסר ב-GitHub.")
        else:
            st.info("מנסה להתחבר לקובץ...")
            # כאן יבוא קוד הסנכרון שכתבנו קודם

    st.write("---")
    st.write("אם אתה רואה את ההודעה הזו, האפליקציה רצה בהצלחה!")

if __name__ == "__main__":
    main()
