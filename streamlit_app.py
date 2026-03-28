import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.graph_objects as go
from datetime import datetime

# --- DB CONNECTION ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("Database Connection Error. Check Secrets.")
    st.stop()

# --- APP CONFIG ---
st.set_page_config(page_title="THYWILL CLINIC", layout="wide")
CURRENCY = "UGX"

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
                else: st.error("Access Denied.")
            except: st.error("Staff database error.")
    st.stop()

# --- HELPER: SAFE DATA FETCH ---
def get_df(table):
    try:
        res = supabase.table(table).select("*").execute()
        df = pd.DataFrame(res.data)
        return df
    except:
        return pd.DataFrame()

# --- SIDEBAR ---
menu = ["Reception", "Triage", "Doctor Desk", "Laboratory", "Maternity & FP", "Pharmacy", "Nursing", "Accounts & Expenses", "Inventory", "Staff", "System Settings"]
choice = st.sidebar.selectbox("Modules", menu)

# --- 1. RECEPTION ---
if choice == "Reception":
    st.header("📋 Detailed Patient Registration")
    with st.form("reg"):
        col1, col2 = st.columns(2)
        name = col1.text_input("Full Name")
        address = col1.text_area("Home Address")
        dob = col2.date_input("Date of Birth")
        gender = col2.selectbox("Gender", ["Male", "Female"])
        is_sub = st.checkbox("Sub-client of another (for billing)?")
        payer_id = None
        patients_df = get_df("patients")
        if is_sub and not patients_df.empty:
            payer = st.selectbox("Select Payer", patients_df['full_name'].tolist())
            payer_id = int(patients_df[patients_df['full_name'] == payer]['id'].values[0])
        
        if st.form_submit_button("Register Patient"):
            supabase.table("patients").insert({"full_name": name, "address": address, "dob": str(dob), "gender": gender, "is_sub_client": is_sub, "payer_id": payer_id}).execute()
            st.success("Patient Registered.")

# --- 2. TRIAGE ---
elif choice == "Triage":
    st.header("🌡️ Triage (Uganda Guidelines)")
    patients_df = get_df("patients")
    if not patients_df.empty:
        p_name = st.selectbox("Select Patient", patients_df['full_name'].tolist())
        p_id = int(patients_df[patients_df['full_name'] == p_name]['id'].values[0])
        col1, col2 = st.columns(2)
        sys = col1.number_input("Systolic BP", 60, 250, 120)
        dia = col1.number_input("Diastolic BP", 40, 150, 80)
        weight = col1.number_input("Weight (kg)", 0.0, 200.0, 70.0)
        temp = col2.number_input("Temp (°C)", 30.0, 45.0, 36.5)
        spo2 = col2.number_input("SpO2 (%)", 0, 100, 98)
        loc = col2.selectbox("Send To:", ["OPD", "Maternity", "Family Planning"])
        
        if temp > 37.5: st.error("🚨 ALERT: FEVER")
        if sys > 140 or dia > 90: st.error("🚨 ALERT: HYPERTENSION")
        
        if st.button("Save Vitals"):
            supabase.table("triage").insert({"patient_id": p_id, "sys": sys, "dia": dia, "temp": temp, "spo2": spo2, "weight": weight, "location": loc}).execute()
            st.success("Vitals Saved.")

# --- 3. DOCTOR DESK ---
elif choice == "Doctor Desk":
    st.header("👨‍⚕️ Clinician Consultation")
    t_df = get_df("triage")
    if not t_df.empty:
        st.write("Recent Triage Records (Weight/BP):")
        st.dataframe(t_df.tail(5))
        
        p_id = st.number_input("Patient ID to treat", step=1)
        history = st.text_area("History Taking")
        exam = st.text_area("Physical Examination")
        diagnosis = st.text_input("Final Diagnosis")
        
        meds_df = get_df("inventory")
        if not meds_df.empty:
            med = st.selectbox("Select Drug", meds_df['item_name'].tolist())
            dosage = st.text_input("Dosage")
            if st.button("Save & Bill"):
                supabase.table("consultations").insert({"patient_id": p_id, "history": history, "exam": exam, "diagnosis": diagnosis}).execute()
                st.success("Record Saved.")

# --- 5. MATERNITY & FP ---
elif choice == "Maternity & FP":
    st.header("🤰 Maternity & Family Planning")
    p_df = get_df("patients")
    if not p_df.empty:
        p_name = st.selectbox("Select Mother/Client", p_df['full_name'].tolist())
        p_id = int(p_df[p_df['full_name'] == p_name]['id'].values[0])
        
        section = st.radio("Section", ["Antenatal (ANC)", "Labor (Partograph)", "Postpartum", "Family Planning"])
        
        if section == "Family Planning":
            method = st.selectbox("Method", ["Injectable", "Implant", "IUD", "Pills"])
            r_date = st.date_input("Return Date")
            if st.button("Save FP Record"):
                supabase.table("maternity_records").insert({"patient_id": p_id, "category": "FP", "notes": method, "return_date": str(r_date)}).execute()
        
        elif section == "Labor (Partograph)":
            dil = st.slider("Dilation (cm)", 4, 10)
            fhr = st.number_input("Fetal Heart Rate", 100, 180, 140)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[0, 4], y=[4, dil], name="Progress"))
            fig.add_trace(go.Scatter(x=[0, 6], y=[4, 10], name="Alert Line", line=dict(dash='dash')))
            st.plotly_chart(fig)

# --- 6. PHARMACY ---
elif choice == "Pharmacy":
    st.header("💊 Pharmacy POS")
    inv_df = get_df("inventory")
    if not inv_df.empty:
        item = st.selectbox("Select Item", inv_df['item_name'].tolist())
        qty = st.number_input("Qty", 1)
        discount = st.number_input("Discount (UGX)", 0)
        price = inv_df[inv_df['item_name'] == item]['selling_price'].values[0]
        total = (price * qty) - discount
        st.subheader(f"Total: {CURRENCY} {total:,.0f}")
        if st.button("Sell Now"):
            st.success("Sale Completed.")

# --- 7. NURSING ---
elif choice == "Nursing":
    st.header("💉 Nursing Section")
    tab1, tab2 = st.tabs(["In-patient Monitoring", "Shift Handover"])
    with tab1:
        p_id = st.number_input("Admitted Patient ID", step=1)
        med_given = st.text_input("Medicine Administered")
        n_temp = st.number_input("Vitals: Temp", 36.5)
        if st.button("Log Vitals & Meds"):
            supabase.table("nursing_monitoring").insert({"patient_id": p_id, "med_given": med_given, "temp": n_temp}).execute()
            st.success("Monitoring updated.")

# --- 11. SYSTEM SETTINGS ---
elif choice == "System Settings":
    st.header("⚙️ System Settings & Pricing")
    set_df = get_df("system_settings")
    if not set_df.empty:
        st.dataframe(set_df)
    new_s = st.text_input("Service Name")
    new_p = st.number_input("Price (UGX)", 0)
    if st.button("Update Price List"):
        supabase.table("system_settings").insert({"service_name": new_s, "price": new_p}).execute()
        st.rerun()
