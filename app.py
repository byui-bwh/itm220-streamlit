import streamlit as st
import pandas as pd
import mysql.connector
import os
from mysql.connector import Error
from dotenv import load_dotenv
load_dotenv()

mysql_password = os.getenv("MYSQL_PASSWORD")


# ---------- Database Connection ----------
@st.cache_resource
def get_connection():
    try:
        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=st.secrets["mysql"]["port"],
            database=st.secrets["mysql"]["database"],
            user=st.secrets["mysql"]["user"],
            password=mysql_password
        )
        return conn
    except Error as e:
        st.error(f"Error connecting to MySQL: {e}")
        return None

# ---------- App Layout ----------
st.title("📊 Streamlit + MySQL (AWS RDS)")
conn = get_connection()

if conn:
    cursor = conn.cursor()

    # ---------- Chart from a View ----------
    st.header("📈 Flight Summary Chart (from View)")
    try:
        df_view = pd.read_sql("SELECT * FROM flight_view limit 200", con=conn)
        st.line_chart(df_view.set_index("airlinename")[["flights_count"]])
    except Exception as e:
        st.error(f"Failed to fetch view data: {e}")

    # ---------- Editable Table ----------
    st.header("📝 Edit Employee Table")

    try:
        df_products = pd.read_sql("SELECT * FROM employee", con=conn)
        edited_df = st.data_editor(df_products, num_rows="dynamic", use_container_width=True)

        if st.button("💾 Save Changes"):
            cursor.execute("DELETE FROM employee")
            for _, row in edited_df.iterrows():
                placeholders = ", ".join(["%s"] * len(row))
                columns = ", ".join(row.index)
                sql = f"INSERT INTO employee ({columns}) VALUES ({placeholders})"
                cursor.execute(sql, tuple(row.values))
            conn.commit()
            st.success("employee table updated!")
    except Exception as e:
        st.error(f"Error editing table: {e}")
else:
    st.stop()
