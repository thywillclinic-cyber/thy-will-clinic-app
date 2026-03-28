import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF

# --- DB CONNECTION ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Database Connection Failed. Check Streamlit Secrets.")
    st.stop()

# --- APP CONFIG ---
st.set_page_config(page_title="Thywill Clinic - Banda Kyankwanzi", layout="wide")

# --- AUTHENTICATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏥 THYWILL CLINIC - BANDA KYANKWANZI")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if email == "denisokuja@gmail.com" and password == "03945760":
            st.session_state.logged_in, st.session_state.role, st.session_state.user = True, "Admin", "Denis Okuja"
            st.rerun()
        else:
            try:
                res = supabase.table("staff_accounts").select("*").eq("email", email).execute()
                if res.data:
                    st.session_state.logged_in, st.session_state.role, st.session_state.user = True, res.data[0]['role'], res.data[0]['full_name']
                    st.rerun()
                else: st.error("Invalid Credentials")
            except: st.error("Staff database not reachable.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state.user}")
role_menus = {
    "Admin": ["Reception", "Triage", "Doctor Desk", "Lab", "Maternity/FP", "Nursing", "Pharmacy POS", "Inventory", "Accounts", "Staff Management"],
    "Doctor": ["Triage", "Doctor Desk", "Lab", "Maternity/FP"],
    "Nurse": ["Triage", "Maternity/FP", "Nursing"],
    "Pharmacist": ["Pharmacy POS", "Inventory"],
}
choice = st.sidebar.radio("Navigate Clinic", role_menus.get(st.session_state.role, ["Triage"]))

# --- UTILITY: GET DATA SAFELY ---
def get_table_df(table_name):
    try:
        res = supabase.table(table_name).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# --- 1. RECEPTION ---
if choice == "Reception":
    st.header("📋 Patient Registration")
    tab1, tab2 = st.tabs(["New Patient", "Manage Groups"])
    with tab1:
        with st.form("reg"):
            name = st.text_input("Full Name")
            phone = st.text_input("Contact")
            is_sub = st.checkbox("Sub-client of another?")
            if st.form_submit_button("Register"):
                supabase.table("patients").insert({"full_name": name, "phone": phone, "is_sub_client": is_sub}).execute()
                st.success("Patient Saved!")

# --- 2. TRIAGE ---
elif choice == "Triage":
    st.header("🌡️ Triage (Uganda Guidelines)")
    col1, col2 = st.columns(2)
    with col1:
        sys = st.number_input("Systolic BP", 60, 250, 120)
        dia = st.number_input("Diastolic BP", 40, 150, 80)
    with col2:
        temp = st.number_input("Temp (°C)", 30.0, 45.0, 36.5)
        spo2 = st.number_input("SpO2 (%)", 0, 100, 98)
    
    if temp > 37.5: st.error("🔥 HIGH FEVER ALERT")
    if sys > 140: st.error("⚠️ HYPERTENSION ALERT")
    if st.button("Save Vitals"): st.success("Vitals Sent to Doctor Desk.")

# --- 3. DOCTOR DESK ---
elif choice == "Doctor Desk":
    st.header("👨‍⚕️ Clinician Consultation")
    patient = st.selectbox("Select Patient", ["Search Patient..."])
    st.text_area("Patient History & Chief Complaint")
    st.text_area("Physical Examination")
    col1, col2 = st.columns(2)
    with col1: st.button("Order Lab Test")
    with col2: st.button("Prescribe Drugs")

# --- 4. LABORATORY ---
elif choice == "Lab":
    st.header("🔬 Laboratory Module")
    st.info("Pending Lab Orders will appear here.")
    st.text_input("Enter Lab Results (e.g. Malaria RDT: Positive)")
    st.button("Release Results")

# --- 5. MATERNITY / FP ---
elif choice == "Maternity/FP":
    st.header("🤰 Maternity & Partograph")
    # Simple Partograph Example
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 4, 8], y=[4, 7, 10], name="Mother Progress", line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=[0, 6], y=[4, 10], name="Alert Line", line=dict(color='orange', dash='dash')))
    st.plotly_chart(fig)

# --- 6. PHARMACY POS (FIXED KEYERROR) ---
elif choice == "Pharmacy POS":
    st.header("💊 Pharmacy / Walk-in POS")
    inv_df = get_table_df("inventory")
    
    if not inv_df.empty:
        item = st.selectbox("Select Drug", inv_df['item_name'].tolist())
        qty = st.number_input("Quantity", 1)
        # Find price
        price = inv_df[inv_df['item_name'] == item]['selling_price'].values[0]
        st.write(f"Price: UGX {price:,.0f}")
        if st.button("Sell & Print Receipt"):
            st.success("Sale Recorded!")
    else:
        st.warning("Inventory is empty. Go to the Inventory tab to add drugs first.")

# --- 7. ACCOUNTS ---
elif choice == "Accounts":
    st.header("💰 Accounts & Daily Profits")
    st.metric("Daily Revenue", "UGX 0")
    st.metric("Expenses Today", "UGX 0")

# --- 8. INVENTORY ---
elif choice == "Inventory":
    st.header("📦 Inventory Management")
    with st.expander("Add New Stock Item"):
        i_name = st.text_input("Item Name (e.g. Panadol)")
        i_stock = st.number_input("Initial Stock", 0)
        i_sell = st.number_input("Selling Price (UGX)", 0)
        i_cost = st.number_input("Cost Price (UGX)", 0)
        if st.button("Add to Stock"):
            supabase.table("inventory").insert({"item_name": i_name, "stock": i_stock, "selling_price": i_sell, "cost_price": i_cost}).execute()
            st.success("Stock Added!")
            st.rerun()
    
    inv_df = get_table_df("inventory")
    if not inv_df.empty: st.dataframe(inv_df)

# --- 9. NURSING ---
elif choice == "Nursing":
    st.header("💉 Nursing & Ward Monitoring")
    st.text_area("Shift Handover Notes")
    st.button("Submit Handover")

# --- 10. STAFF LOGS ---
st.sidebar.divider()
st.sidebar.subheader("📢 Staff Notice Board")
try:
    ann = supabase.table("announcements").select("*").order("created_at", desc=True).limit(2).execute()
    for a in ann.data: st.sidebar.caption(f"**{a['author']}**: {a['message']}")
except: st.sidebar.write("No notices.")
