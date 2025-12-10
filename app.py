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

# requirement queries:

queries = {
    "function": "SELECT CONCAT(firstname, ' ', lastname) AS fullname FROM employee",
    "inner join": """SELECT     f.flight_id, 
    f.flightno,
    f.`from`   AS from_airport,
    f.`to`     AS to_airport,
    f.departure,
    f.arrival,
    f.airline_id AS flight_airline_id,
    a.airline_id AS airline_airline_id,
    a.iata,
    a.airlinename,
    a.base_airport FROM flight AS f INNER JOIN airline AS a ON f.airline_id = a.airline_id""",
    "conditional logic": """SELECT
    flight_id,
    flightno,
    TIMESTAMPDIFF(MINUTE, departure, arrival) AS duration_minutes,
    CASE
        WHEN TIMESTAMPDIFF(MINUTE, departure, arrival) < 120
            THEN 'Short Haul'
        WHEN TIMESTAMPDIFF(MINUTE, departure, arrival) BETWEEN 120 AND 360
            THEN 'Medium Haul'
        ELSE 'Long Haul'
    END AS flight_type
FROM flight
ORDER BY duration_minutes;""",
    "outer join": "SELECT * FROM flight LEFT OUTER JOIN airline ON flight.airline_id = airline.airline_id",
    "aggregate function and GROUP BY": "SELECT * FROM flight",
    "subquery": "SELECT * FROM flight",
    "window function": "SELECT * FROM flight"
}


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

# Helper function to deduplicate columns
def dedupe_columns(df):
    seen = {}
    new_columns = []

    for col in df.columns:
        if col not in seen:
            seen[col] = 0
            new_columns.append(col)
        else:
            seen[col] += 1
            new_columns.append(f"{col}_{seen[col]}")

    df.columns = new_columns
    return df


# =============================
# Run Query Function
# =============================
@st.cache_data(show_spinner=False)
def run_query(sql: str, limit: int):
    """
    Executes a SQL query with a LIMIT clause
    and returns a pandas DataFrame.
    """
    if limit:
        sql = f"{sql} LIMIT {limit}"

    conn, tunnel = get_connection()
    df = pd.read_sql(sql, conn)
    conn.close()
    tunnel.stop()
    # Auto-fix duplicate columns (student-friendly)
    df = dedupe_columns(df)

    return df



@st.cache_data
def load_chart_data():
    conn, tunnel = get_connection()
    df = pd.read_sql("SELECT * FROM airportdb.flight_view WHERE `date` BETWEEN '2015-08-01' and '2015-09-01'", conn)
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
    format_strings = ",".join( map(str, ids_to_delete))
    print(f"format_strings: {format_strings}")
    print(f"Deleting rows with IDs: {ids_to_delete}")
    conn, tunnel = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM passenger WHERE passenger_id IN ({format_strings})")
    conn.commit()
    conn.close()

def insert_row(passportno, firstname, lastname):
    conn, tunnel = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO passenger (passportno, firstname, lastname) VALUES (%s, %s, %s)", (passportno, firstname, lastname))
    conn.commit()
    conn.close()

# ---------- HELPER FUNCTIONS ----------

def hash_df(df):
    return hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()

# ---------- STREAMLIT APP ----------

st.title("📊 Flight Analytics and Passenger Dashboard")

# Line chart from DB view
st.subheader("📈 Flight Counts")
chart_df = load_chart_data()
chart_df['date'] = pd.to_datetime(chart_df['date'])
pivot_df = chart_df.pivot(index='date', columns='airlinename', values='flights_count')
st.line_chart(pivot_df)

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
        print(f"Deleting rows with IDs: {selected_ids}")
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

# Selectbox for requirement queries with limit slider

# =============================
# UI for queries
# =============================

st.title("SQL Query Explorer")
selected_option = st.selectbox(
    "Choose a SQL concept:",
    options=list(queries.keys())
)

# Row limit control
row_limit = st.slider(
    "Row limit",
    min_value=10,
    max_value=1000,
    value=100,
    step=10
)
# Show SQL toggle
with st.expander("Preview SQL"):
    st.code(queries[selected_option], language="sql")

# Run Query Button
if st.button("Run Query", type="primary"):
    with st.spinner("Running query..."):
        try:
            df = run_query(queries[selected_option], row_limit)

            st.success(f"Results for **{selected_option}**")
            st.dataframe(df, use_container_width=True)

            st.caption(f"Rows returned: {len(df)}")

        except Exception as e:
            st.error("Query execution failed")
            st.exception(e)


# End of Streamlit app

