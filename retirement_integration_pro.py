import os

def get_coefficient_from_excel(gender, birth_date, ret_year, assets, coverage_pct, guarantee_months):
    try:
        # נתיב לקובץ המקור ולקובץ זמני (למניעת בעיות הרשאות בשרת)
        source_file = 'simulator_prisha.xlsm'
        temp_file = '/tmp/temp_sim.xlsm' if os.path.exists('/tmp') else 'temp_sim.xlsm'
        
        # טעינת הקובץ
        wb = openpyxl.load_workbook(source_file, keep_vba=True, data_only=False)
        if 'חישוב זקנה' not in wb.sheetnames:
            st.error(f"גיליון 'חישוב זקנה' לא נמצא. הגיליונות הקיימים: {wb.sheetnames}")
            return None, None
            
        sheet = wb['חישוב זקנה']
        
        # הזנת נתונים - וודא שהתאים האלו אכן פתוחים לעריכה באקסל
        sheet['C14'] = birth_date.strftime('%d/%m/%Y')
        sheet['C13'] = int(ret_year)
        sheet['C15'] = "זכר" if gender == "גבר" else "נקבה"
        sheet['C18'] = float(assets)
        sheet['C20'] = float(coverage_pct) / 100
        sheet['C21'] = int(guarantee_months)
        
        # שמירה
        wb.save(temp_file)
        
        # טעינה מחדש של הערכים המחושבים
        # הערה: openpyxl לא תמיד מצליחה לחשב נוסחאות XLSM מורכבות ללא אקסל מותקן
        wb_res = openpyxl.load_workbook(temp_file, data_only=True)
        sheet_res = wb_res['חישוב זקנה']
        
        coeff = sheet_res['C28'].value
        pension = sheet_res['C29'].value
        
        # בדיקה אם הערך הוא נוסחה (אם קיבלנו מחרוזת שמתחילה ב-= במקום מספר)
        if isinstance(coeff, str) and coeff.startswith('='):
            st.warning("השרת מחזיר את הנוסחה ולא את הערך המחושב. ייתכן והאקסל מוגן או דורש חישוב ידני.")
            
        return coeff, pension
    except Exception as e:
        st.error(f"שגיאה טכנית בסנכרון: {e}")
        return None, None
