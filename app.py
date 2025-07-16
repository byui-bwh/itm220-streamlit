import streamlit as st
import pandas as pd
import mysql.connector
import os
import hashlib
from mysql.connector import Error
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv
load_dotenv()

mysql_password = os.getenv("MYSQL_PASSWORD")
mysql_password_local = os.getenv("MYSQL_PASSWORD_LOCAL")


# Set up SSH tunnel


# ---------- Database Connection ----------
def get_connection():
    try:
        server = SSHTunnelForwarder(
        (st.secrets["ssh"]["ssh_host"], 22),
        ssh_username=st.secrets["ssh"]["ssh_user"],
        ssh_pkey=st.secrets["ssh"]["ssh_pem_path"],
        remote_bind_address=(st.secrets["mysql"]["host"], st.secrets["mysql"]["port"]),
            )
        
        server.start()
        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=server.local_bind_port,
            database=st.secrets["mysql"]["database"],
            user=st.secrets["mysql"]["user"],
            password=mysql_password_local
        )
        return conn, server
    except Error as e:
        st.error(f"Error connecting to MySQL: {e}")
        return None
    
@st.cache_data
def load_passengers():
    conn, tunnel = get_connection()
    df = pd.read_sql("SELECT * FROM passenger", conn)
    conn.close()
    tunnel.stop()
    return df

@st.cache_data
def load_chart_data():
    conn, tunnel = get_connection()
    df = pd.read_sql("SELECT * FROM flight_view", conn)
    conn.close()
    tunnel.stop()
    return df

def update_rows(updated_df, original_df):
    conn = get_connection()
    cursor = conn.cursor()
    
    for i, row in updated_df.iterrows():
        original_row = original_df.loc[i]
        if not row.equals(original_row):
            cursor.execute(
                "UPDATE passenger SET passportno=%s, firstname=%s, lastname=%s WHERE passenger_id=%s",
                (row['passportno'], row['firstname'], row['lastname'], row['passenger_id'])
            )
    conn.commit()
    conn.close()

def delete_rows(ids_to_delete):
    conn = get_connection()
    cursor = conn.cursor()
    format_strings = ','.join(['%s'] * len(ids_to_delete))
    print(ids_to_delete)
    cursor.execute(f"DELETE FROM passenger WHERE passenger_id IN ({format_strings})", tuple(ids_to_delete))
    conn.commit()
    conn.close()

def insert_row(passportno, firstname, lastname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO passenger (passportno, firstname, lastname) VALUES (%s, %s, %s)", (passportno, firstname, lastname))
    conn.commit()
    conn.close()

# ---------- HELPER FUNCTIONS ----------

def hash_df(df):
    return hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()

# ---------- STREAMLIT APP ----------

st.title("📊 User Management Dashboard")

# Line chart from DB view
st.subheader("📈 Flight Counts")
chart_df = load_chart_data()
st.line_chart(chart_df.set_index("airlinename")[["flights_count"]])

# Editable table
st.subheader("👤 Manage Passengers (Add, Edit, Delete)")

# Load passengers table
if "original_df" not in st.session_state:
    st.session_state.original_df = load_passengers()

df = st.session_state.original_df.copy()
df["delete"] = False
edited_df = st.data_editor(df, num_rows="fixed", hide_index=True, column_order=("passportno", "firstname", "lastname", "delete"), use_container_width=True)


# Load initial data
if "original_df" not in st.session_state:
    st.session_state.original_df = load_passengers()
    st.session_state.original_hash = hash_df(st.session_state.original_df)

df = st.session_state.original_df.copy()

# Delete selected rows
if st.button("🗑️ Delete Selected Rows"):
    selected_ids = edited_df[edited_df["delete"] == True]["passenger_id"].tolist()
    if selected_ids:
        delete_rows(selected_ids)
        st.session_state.original_df = load_passengers()
        st.session_state.original_hash = hash_df(st.session_state.original_df)
        st.success(f"Deleted {len(selected_ids)} row(s).")
        st.rerun()
    else:
        st.info("No rows selected for deletion.")

# Save edits
if st.button("💾 Save Edits"):
    edited_df = edited_df.drop(columns=["delete"])
    new_hash = hash_df(edited_df)
    if new_hash != st.session_state.original_hash:
        update_rows(edited_df, st.session_state.original_df)
        st.session_state.original_df = edited_df
        st.session_state.original_hash = new_hash
        st.success("Changes saved.")
    else:
        st.info("No changes detected.")

# Insert new row
st.subheader("➕ Add New Passenger")
with st.form("insert_form"):
    new_passportno = st.text_input("Passport Number")
    new_firstname = st.text_input("First Name")
    new_lastname = st.text_input("Last Name")
    submitted = st.form_submit_button("Add Passenger")

    if submitted:
        if new_passportno.strip() == "" or new_firstname.strip() == "" or new_lastname.strip() == "":
            st.warning("Passport Number, First Name, and Last Name are required.")
        else:
            insert_row(new_passportno.strip(), new_firstname.strip(), new_lastname.strip())
            st.session_state.original_df = load_passengers()
            st.session_state.original_hash = hash_df(st.session_state.original_df)
            st.success(f"Passenger '{new_firstname}' '{new_lastname}' added.")
            st.rerun()


