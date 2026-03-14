import streamlit as st
import pandas as pd

def get_menora_coeff(birth_year, retirement_age):
    # טבלת מנורה יוני 2025 - דגימה לפי שנת לידה 1960 (מתוך נספחי התקנון)
    # גיל: מקדם
    menora_table = {
        60: 214.98, 61: 210.42, 62: 207.10, 63: 203.67, 
        64: 200.13, 65: 196.45, 66: 191.01, 67: 187.08, 
        68: 183.04, 69: 178.88, 70: 174.58
    }
    
    # חישוב אינטרפולציה ליניארית בין גילאים מלאים
    age_floor = int(retirement_age)
    age_ceil = age_floor + 1
    
    if age_floor in menora_table and age_ceil in menora_table:
        val_floor = menora_table[age_floor]
        val_ceil = menora_table[age_ceil]
        fraction = retirement_age - age_floor
        # ככל שהגיל עולה, המקדם יורד
        return round(val_floor - (val_floor - val_ceil) * fraction, 2)
    return menora_table.get(age_floor, 190.0)

def main():
    st.title("מחשבון פרישה - מנורה מבטחים (יוני 2025)")
    
    with st.sidebar:
        st.header("נתוני בסיס")
        birth_year = st.selectbox("שנת לידה", range(1950, 1975), index=10) # 1960
        ret_age = st.slider("גיל פרישה (שנים וחודשים)", 60.0, 70.0, 67.0, 0.083)
        
        target_coeff = get_menora_coeff(birth_year, ret_age)
        st.metric("מקדם לפי תקנון מנורה", target_coeff)

    # הצגת טבלת הצבירות
    if 'funds' not in st.session_state:
        st.session_state.funds = [{'name': 'מנורה מקיפה', 'amount': 1200000.0}]

    for i, fund in enumerate(st.session_state.funds):
        cols = st.columns([3, 2, 1])
        fund['name'] = cols[0].text_input("קופה", fund['name'], key=f"n_{i}")
        fund['amount'] = cols[1].number_input("צבירה", fund['amount'], key=f"a_{i}")
        cols[2].number_input("מקדם מסונכרן", value=target_coeff, disabled=True, key=f"c_{i}")

    pension = sum(f['amount'] for f in st.session_state.funds) / target_coeff
    st.success(f"קצבה חודשית ברוטו: ₪{pension:,.0f}")

if __name__ == "__main__":
    main()
