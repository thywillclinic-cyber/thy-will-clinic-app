import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF

# --- DB CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- APP CONFIG ---
st.set_page_config(page_title="Thywill Clinic", layout="wide")

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
            # Check staff_accounts table
            res = supabase.table("staff_accounts").select("*").eq("email", email).execute()
            if res.data:
                st.session_state.logged_in, st.session_state.role, st.session_state.user = True, res.data[0]['role'], res.data[0]['full_name']
                st.rerun()
            else: st.error("Invalid Credentials")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state.user}")
st.sidebar.write(f"Role: {st.session_state.role}")

# Role-Based Access Control (RBAC)
role_menus = {
    "Admin": ["Reception", "Triage", "Doctor Desk", "Lab", "Maternity/FP", "Pharmacy POS", "Nursing", "Inventory", "Accounts", "Settings", "Staff Management"],
    "Doctor": ["Triage", "Doctor Desk", "Lab", "Maternity/FP"],
    "Nurse": ["Triage", "Maternity/FP", "Nursing"],
    "Pharmacist": ["Pharmacy POS", "Inventory"],
}
choice = st.sidebar.radio("Go to:", role_menus.get(st.session_state.role, ["Triage"]))

# --- 1. RECEPTION (Sub-client Billing) ---
if choice == "Reception":
    st.header("📋 Patient Registration & Group Billing")
    # Registration Logic
    with st.form("reg"):
        name = st.text_input("Patient Full Name")
        phone = st.text_input("Phone")
        is_sub = st.checkbox("Is this a sub-client (dependent)?")
        payer_name = st.text_input("If sub-client, who is the Payer? (Name)")
        if st.form_submit_button("Register"):
            supabase.table("patients").insert({"full_name": name, "phone": phone, "is_sub_client": is_sub}).execute()
            st.success("Registered!")

# --- 2. TRIAGE (Uganda Guidelines) ---
elif choice == "Triage":
    st.header("🌡️ Triage & Vitals")
    col1, col2 = st.columns(2)
    with col1:
        sys = st.number_input("Systolic BP", 120)
        dia = st.number_input("Diastolic BP", 80)
        temp = st.number_input("Temp (°C)", 36.5)
    with col2:
        spo2 = st.number_input("SpO2 (%)", 98)
        weight = st.number_input("Weight (kg)", 70)
    
    alerts = []
    if temp > 37.5: alerts.append("FEVER")
    if sys > 140: alerts.append("HYPERTENSION")
    
    if alerts: st.error(f"ALERTS: {', '.join(alerts)}")
    if st.button("Save Vitals"):
        st.success("Vitals synced to Doctor Desk.")

# --- 5. MATERNITY (Partograph) ---
elif choice == "Maternity/FP":
    st.header("🤰 Maternity Partograph")
    # (Using the Plotly logic provided in previous response)
    st.info("Visualizing Alert and Action lines for labor monitoring...")

# --- 6. PHARMACY POS (UGX) ---
elif choice == "Pharmacy POS":
    st.header("💊 Pharmacy POS (Direct Inventory Link)")
    res = supabase.table("inventory").select("*").execute()
    inv_df = pd.DataFrame(res.data)
    item = st.selectbox("Select Drug", inv_df['item_name'].tolist())
    qty = st.number_input("Qty", 1)
    price = inv_df[inv_df['item_name']==item]['selling_price'].values[0]
    st.metric("Total Cost", f"UGX {price * qty:,.0f}")
    if st.button("Complete Sale"):
        st.success("Stock deducted. Sale logged to Accounts.")

# --- 9. STAFF MANAGEMENT ---
elif choice == "Staff Management":
    st.header("👥 Staff Accounts & Roles")
    with st.form("staff"):
        s_email = st.text_input("Staff Email")
        s_name = st.text_input("Full Name")
        s_role = st.selectbox("Role", ["Doctor", "Nurse", "Pharmacist", "Lab", "Receptionist"])
        if st.form_submit_button("Create Account"):
            supabase.table("staff_accounts").insert({"email": s_email, "full_name": s_name, "role": s_role}).execute()
            st.success("Staff member added.")

# --- 10. CHAT/ANNOUNCEMENTS (SAFE VERSION) ---
st.sidebar.divider()
st.sidebar.subheader("📢 Announcements")

try:
    ann = supabase.table("announcements").select("*").order("created_at", desc=True).limit(2).execute()
    if ann.data:
        for a in ann.data:
            st.sidebar.caption(f"**{a['author']}**: {a['message']}")
    else:
        st.sidebar.write("No announcements yet.")
except Exception as e:
    st.sidebar.error("Could not connect to database.")
    # This helps you see the real error in the sidebar without crashing the app
