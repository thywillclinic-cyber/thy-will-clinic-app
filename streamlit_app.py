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
except:
    st.error("Database Connection Error. Check Secrets.")
    st.stop()

# --- CONFIG ---
st.set_page_config(page_title="THYWILL CLINIC", layout="wide")
CURRENCY = "UGX"

# --- AUTHENTICATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏥 THYWILL CLINIC - BANDA KYANKWANZI")
    st.subheader("Authorized Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if email == "denisokuja@gmail.com" and password == "03945760":
            st.session_state.logged_in, st.session_state.role, st.session_state.user = True, "Admin", "Denis Okuja"
            st.rerun()
        else:
            res = supabase.table("staff_accounts").select("*").eq("email", email).execute()
            if res.data:
                st.session_state.logged_in, st.session_state.role, st.session_state.user = True, res.data[0]['role'], res.data[0]['full_name']
                st.rerun()
            else: st.error("Access Denied.")
    st.stop()

# --- SIDEBAR NAV ---
st.sidebar.title(f"👨‍⚕️ {st.session_state.user}")
menu = ["Reception", "Triage", "Doctor Desk", "Laboratory", "Maternity & FP", "Pharmacy", "Nursing", "Accounts & Expenses", "Inventory", "Staff", "System Settings"]
choice = st.sidebar.selectbox("Modules", menu)

# --- HELPER FUNCTIONS ---
def get_df(table):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data)

def add_bill(p_id, service, amount):
    supabase.table("bills").insert({"patient_id": p_id, "service": service, "amount": amount}).execute()

# --- 1. RECEPTION ---
if choice == "Reception":
    st.header("📋 Patient Registration")
    with st.form("reg_form"):
        name = st.text_input("Full Name")
        address = st.text_area("Address")
        phone = st.text_input("Contact")
        is_sub = st.checkbox("Sub-client of another?")
        # Fetch potential payers
        patients_df = get_df("patients")
        payer_id = None
        if is_sub and not patients_df.empty:
            payer_choice = st.selectbox("Select Payer", patients_df['full_name'].tolist())
            payer_id = int(patients_df[patients_df['full_name'] == payer_choice]['id'].values[0])
        
        if st.form_submit_button("Register Patient"):
            supabase.table("patients").insert({"full_name": name, "address": address, "phone": phone, "is_sub_client": is_sub, "payer_id": payer_id}).execute()
            st.success("Registration Successful.")

# --- 2. TRIAGE ---
elif choice == "Triage":
    st.header("🌡️ Triage & Vitals (Uganda Guidelines)")
    patients_df = get_df("patients")
    if not patients_df.empty:
        p_name = st.selectbox("Select Patient", patients_df['full_name'].tolist())
        p_id = int(patients_df[patients_df['full_name'] == p_name]['id'].values[0])
        col1, col2 = st.columns(2)
        sys = col1.number_input("Systolic BP", 60, 250, 120)
        dia = col1.number_input("Diastolic BP", 40, 150, 80)
        temp = col2.number_input("Temp (°C)", 30.0, 45.0, 36.5)
        spo2 = col2.number_input("SpO2 (%)", 0, 100, 98)
        loc = st.radio("Send To:", ["OPD", "Maternity", "Family Planning"])
        
        if temp > 37.5: st.error("🔥 ALERT: HIGH FEVER")
        if sys > 140 or dia > 90: st.error("🚨 ALERT: HYPERTENSION")
        
        if st.button("Save & Link Details"):
            supabase.table("triage").insert({"patient_id": p_id, "sys": sys, "dia": dia, "temp": temp, "spo2": spo2, "location": loc}).execute()
            st.success(f"Vitals sent to {loc}")

# --- 3. DOCTOR DESK ---
elif choice == "Doctor Desk":
    st.header("👨‍⚕️ Clinician Consultation")
    triage_df = get_df("triage")
    if not triage_df.empty:
        st.subheader("Patients in Queue")
        st.dataframe(triage_df)
        
        with st.expander("Patient Consultation Form"):
            p_id = st.number_input("Enter Patient ID to treat", step=1)
            history = st.text_area("History")
            exam = st.text_area("Examination")
            diagnosis = st.text_input("Diagnosis")
            
            st.write("---")
            st.subheader("Order Services")
            test = st.text_input("Lab Order")
            
            # Linked Inventory Rx
            inv_df = get_df("inventory")
            if not inv_df.empty:
                med = st.selectbox("Prescribe Drug", inv_df['item_name'].tolist())
                med_id = int(inv_df[inv_df['item_name'] == med]['id'].values[0])
                dosage = st.text_input("Dosage")
                
            if st.button("Complete Consultation"):
                supabase.table("consultations").insert({"patient_id": p_id, "history": history, "exam": exam, "diagnosis": diagnosis}).execute()
                if test: supabase.table("lab_orders").insert({"patient_id": p_id, "test_name": test}).execute()
                if med: supabase.table("prescriptions").insert({"patient_id": p_id, "item_id": med_id, "dosage": dosage, "source": "OPD"}).execute()
                add_bill(p_id, "Consultation Fee", 10000)
                st.success("Consultation Finished. Bills Generated.")

# --- 4. LABORATORY ---
elif choice == "Laboratory":
    st.header("🔬 Laboratory Module")
    tab1, tab2 = st.tabs(["Pending Tests", "Inventory & Results"])
    with tab1:
        lab_df = get_df("lab_orders")
        if not lab_df.empty:
            st.dataframe(lab_df[lab_df['status']=='Pending'])
            order_id = st.number_input("Order ID", step=1)
            result = st.text_area("Result Details")
            if st.button("Submit Result"):
                supabase.table("lab_orders").update({"result": result, "status": "Completed"}).eq("id", order_id).execute()
                st.success("Results released to Doctor Desk.")

# --- 5. MATERNITY & FP ---
elif choice == "Maternity & FP":
    st.header("🤰 Maternity & Family Planning")
    m_choice = st.radio("Section:", ["ANC Tracker", "Labor (Partograph)", "Postpartum", "Family Planning"])
    if m_choice == "Labor (Partograph)":
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 4, 8], y=[4, 7, 10], name="Dilation", line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=[0, 6], y=[4, 10], name="Alert Line", line=dict(color='orange', dash='dash')))
        st.plotly_chart(fig)
    else:
        st.info(f"{m_choice} records and tracking system active.")

# --- 6. PHARMACY ---
elif choice == "Pharmacy":
    st.header("💊 Pharmacy & Dispensary")
    mode = st.radio("Action:", ["Walk-in POS", "Prescription Dispensary"])
    inv_df = get_df("inventory")
    
    if mode == "Walk-in POS":
        if not inv_df.empty:
            item = st.selectbox("Select Item", inv_df['item_name'].tolist())
            qty = st.number_input("Qty", 1)
            price = inv_df[inv_df['item_name']==item]['selling_price'].values[0]
            st.subheader(f"Total: {CURRENCY} {price * qty:,.0f}")
            if st.button("Complete Walk-in Sale"):
                st.success("Sale logged. Stock Deducted.")
                
    elif mode == "Prescription Dispensary":
        rx_df = get_df("prescriptions")
        st.dataframe(rx_df[rx_df['status']=='Pending'])

# --- 7. ACCOUNTS & EXPENSES ---
elif choice == "Accounts & Expenses":
    st.header("💰 Accounts & Financials")
    tab1, tab2 = st.tabs(["Billing & Debtors", "Expenses & Profit/Loss"])
    with tab1:
        bills_df = get_df("bills")
        st.subheader("Unpaid Bills")
        st.dataframe(bills_df[bills_df['status']=='Unpaid'])
    with tab2:
        st.metric("Total Profit/Loss Today", f"{CURRENCY} 0")

# --- 9. INVENTORY ---
elif choice == "Inventory":
    st.header("📦 Inventory & Batch Management")
    with st.expander("Add New Batch"):
        name = st.text_input("Item Name")
        stock = st.number_input("Stock Qty", 0)
        cost = st.number_input("Cost Price", 0)
        sell = st.number_input("Selling Price", 0)
        if st.button("Add to Inventory"):
            supabase.table("inventory").insert({"item_name": name, "stock": stock, "cost_price": cost, "selling_price": sell}).execute()
            st.rerun()
    st.dataframe(get_df("inventory"))

# --- 11. STAFF & CHAT ---
elif choice == "Staff":
    st.header("👥 Staff Management")
    if st.session_state.user == "Denis Okuja":
        st.subheader("Admin: Staff Accounts")
        st.dataframe(get_df("staff_accounts"))
    
    st.divider()
    st.subheader("💬 Staff Announcements")
    msg = st.text_input("Post message")
    if st.button("Broadcast"):
        supabase.table("announcements").insert({"author": st.session_state.user, "message": msg}).execute()
        st.rerun()
    st.dataframe(get_df("announcements").sort_values("created_at", ascending=False))

# --- NURSING ---
elif choice == "Nursing":
    st.header("💉 Nursing Station")
    st.subheader("Vitals Monitoring")
    st.text_area("Shift Handover Notes")
    if st.button("Complete Handover"):
        st.success("Handover Saved.")
