import streamlit as st
import pandas as pd
import numpy as np
import time
from streamlit_autorefresh import st_autorefresh

# ----- AI CARD HELPER (Streamlit-native, all text white) -----
def ai_card(contents, machine=None, button_key=None):
    scheduled = False
    with st.container():
        st.markdown(
            f"""
            <div style='background:rgba(56,189,248,0.08);border-radius:14px;padding:18px 20px 12px 20px;
                margin-bottom:8px;border:1.5px solid rgba(8,145,178,0.13);box-shadow:0 4px 12px #0001;'>
            {contents}
            </div>
            """,
            unsafe_allow_html=True
        )
        col1, col2 = st.columns([3, 1])
        with col2:
            if machine:
                if st.button(f"🛠️ Schedule ({machine})", key=button_key):
                    st.session_state.attn_from_operator.add(machine)
                    scheduled = True
    return scheduled

st.set_page_config(page_title="Smart Predictive Maintenance", layout="wide")

# --------- Demo Mode Toggle in Sidebar ---------
demo_mode = st.sidebar.checkbox("Demo Mode (auto-refresh and random alerts)", value=True)
if demo_mode:
    st_autorefresh(interval=10000, key="auto_refresh")

# --------- In-Memory State for Log/Acks/Repaired/Tickets/Operator-Attn ---------
if "ack_log" not in st.session_state:
    st.session_state.ack_log = {}
if "repaired_machines" not in st.session_state:
    st.session_state.repaired_machines = set()
if "scheduled_repairs" not in st.session_state:
    st.session_state.scheduled_repairs = set()
if "approved_tickets" not in st.session_state:
    st.session_state.approved_tickets = set()
if "attn_from_operator" not in st.session_state:
    st.session_state.attn_from_operator = set()

# --- Real-Time Updatable Maintenance Ticket Data ---
if "maint_df" not in st.session_state:
    maint_data = [
        {"Ticket #": "MT-001", "Machine": "Mixer-01", "Type": "Predictive", "Reason": "Bearing wear", "Created": "2025-06-03 11:10", "Due": "2025-06-03 14:00", "Assigned To": "Ali", "Status": "Queue"},
        {"Ticket #": "MT-002", "Machine": "Conveyor-02", "Type": "Preventive", "Reason": "Motor check", "Created": "2025-06-03 10:50", "Due": "2025-06-04 09:00", "Assigned To": "Maria", "Status": "Assigned"},
        {"Ticket #": "MT-003", "Machine": "Pump-03", "Type": "Corrective", "Reason": "Sensor fault", "Created": "2025-06-02 15:15", "Due": "2025-06-03 11:00", "Assigned To": "Sohail", "Status": "Completed"}
    ]
    st.session_state.maint_df = pd.DataFrame(maint_data)

# ------- Realistic Machine Names -------
num_machines = 4
industry_names = [
    "Mixer-01", "Conveyor-02", "Pump-03", "Dryer-04", "Chiller-05", "Press-06",
    "Blender-07", "Boiler-08", "Filter-09", "Separator-10"
]
machine_names = industry_names[:num_machines]
num_samples = 120  # 2 hours of 1-min samples
times = pd.date_range(end=pd.Timestamp.now(), periods=num_samples, freq='min')

# ---- AI Failure Risk Function ----
def predict_failure_risk(temp_values, vib_values):
    temp_recent = np.array(temp_values[-10:])
    vib_recent = np.array(vib_values[-10:])
    temp_risk = np.clip((temp_recent.mean() - 70) / 30, 0, 1)
    vib_risk = np.clip((vib_recent.mean() - 1) / 2, 0, 1)
    risk_score = (0.6 * temp_risk + 0.4 * vib_risk)
    return int(risk_score * 100)

def simulate_machine_profile(name):
    if name in st.session_state.repaired_machines:
        base_temp = 68 + np.random.normal(0, 0.7, num_samples)
        base_vibration = 1.0 + np.random.normal(0, 0.1, num_samples)
        risk = ["Low"] * num_samples
    elif name == machine_names[2]:
        base_temp = 75 + np.linspace(0, 20, num_samples) + np.random.normal(0, 2, num_samples)
        base_vibration = 1.4 + np.linspace(0, 2, num_samples) + np.random.normal(0, 0.18, num_samples)
        risk = ["High"] * num_samples
    elif name == machine_names[1]:
        base_temp = 72 + np.linspace(0, 6, num_samples) + np.random.normal(0, 1.1, num_samples)
        base_vibration = 1.1 + np.random.normal(0, 0.14, num_samples)
        risk = ["Medium" if t > 77 else "Low" for t in base_temp]
    else:
        base_temp = 68 + np.random.normal(0, 1, num_samples)
        base_vibration = 1.0 + np.random.normal(0, 0.09, num_samples)
        risk = ["Low"] * num_samples

    return pd.DataFrame({
        "Time": times,
        "Temperature (°F)": base_temp,
        "Vibration (g)": base_vibration,
        "Risk": risk
    })

# -- Build new dummy data on each run (so it's "live")
machine_data = {}
for name in machine_names:
    machine_data[name] = simulate_machine_profile(name)

def random_alerts():
    alerts = []
    for name in machine_names:
        df = machine_data[name]
        last_temp = df["Temperature (°F)"].iloc[-1]
        last_risk = df["Risk"].iloc[-1]
        if last_risk == "High":
            alerts.append({
                "Machine": name,
                "Alert": "Bearing temp high" if last_temp > 85 else "Vibration above normal",
                "Severity": "High",
                "Time": time.strftime('%H:%M')
            })
        elif last_risk == "Medium":
            alerts.append({
                "Machine": name,
                "Alert": "Temperature rising" if last_temp > 77 else "Vibration above normal",
                "Severity": "Medium",
                "Time": time.strftime('%H:%M')
            })
    if not alerts:
        alerts.append({
            "Machine": machine_names[2],
            "Alert": "Bearing temp high",
            "Severity": "High",
            "Time": time.strftime('%H:%M')
        })
    return alerts

all_alerts = random_alerts()

env_temp = int(np.clip(70 + np.random.normal(0, 2), 66, 85))
env_humidity = int(np.clip(47 + np.random.normal(0, 4), 40, 65))
env_co2 = int(np.clip(500 + np.random.normal(0, 60), 400, 900))
env_air_quality = "Good" if env_co2 < 600 else "Alert"

role = st.sidebar.selectbox("Select Role", ["Operator", "Maintenance", "Supervisor"])
st.sidebar.markdown("---")
selected_machine = st.sidebar.selectbox("View Machine Detail", ["All"] + machine_names)
with st.sidebar.expander("ℹ️ About / How This Works"):
    st.markdown("""
<span style='color:white'>
<b>This dashboard simulates a modern factory's predictive maintenance:</b>  
- IoT sensors feed live data (temperature, vibration, environment)
- Machine Learning predicts failures before they happen  
- Role-based dashboards for Operator, Maintenance, and Supervisor  
- All actions/alerts/tickets are logged and can be exported  
- Demo mode lets you see risks, alerts, and repairs in real time!  
</span>
""", unsafe_allow_html=True)
st.sidebar.markdown("<span style='color:white'><b>How does our AI/ML predict failures?</b></span>", unsafe_allow_html=True)
st.sidebar.info("Our system uses temperature and vibration data trends from IoT sensors. ML models compare new readings to historical patterns, flagging abnormal rises in vibration/temperature that indicate likely bearing or motor wear. Predictive alerts help prevent breakdowns before they occur.")

if any(a["Severity"] == "High" for a in all_alerts):
    st.error("🚨 CRITICAL: One or more machines at HIGH RISK! Please check alerts and act immediately.")

st.markdown("<h1 style='color:white'>Smart Predictive Maintenance Dashboard</h1>", unsafe_allow_html=True)
st.caption(f"Last Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

kpi_cols = st.columns(4)
kpi_cols[0].markdown(f"<div style='color:white;font-size:1.1em'>Machines Monitored<br><b style='font-size:1.4em'>{num_machines}</b></div>", unsafe_allow_html=True)
kpi_cols[1].markdown(f"<div style='color:white;font-size:1.1em'>Active Alerts<br><b style='font-size:1.4em'>{sum([1 for a in all_alerts if a['Severity'] in ['High','Medium']])}</b></div>", unsafe_allow_html=True)
kpi_cols[2].markdown(f"<div style='color:white;font-size:1.1em'>High-Risk Machines<br><b style='font-size:1.4em'>{sum([1 for m in machine_data if machine_data[m]['Risk'].iloc[-1] == 'High'])}</b></div>", unsafe_allow_html=True)
kpi_cols[3].markdown(f"<div style='color:white;font-size:1.1em'>Role<br><b style='font-size:1.2em'>{role}</b></div>", unsafe_allow_html=True)

st.write("")

# ========================= OPERATOR DASHBOARD ========================
if role == "Operator":
    st.markdown("<h2 style='color:white'>Operator Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:white'>Machine Status Overview</h4>", unsafe_allow_html=True)
    grid_cols = st.columns(num_machines)
    for i, name in enumerate(machine_names):
        latest = machine_data[name].iloc[-1]
        risk = latest["Risk"]
        temp_values = machine_data[name]["Temperature (°F)"].values
        vib_values = machine_data[name]["Vibration (g)"].values
        fail_risk_percent = predict_failure_risk(temp_values, vib_values)
        color = "#fff"
        icon = "🟥" if risk == "High" else "🟧" if risk == "Medium" else "🟩"
        with grid_cols[i]:
            c1, c2 = st.columns([1.4, 1])
            with c1:
                st.line_chart(machine_data[name][["Temperature (°F)", "Vibration (g)"]].tail(30), use_container_width=True, height=110)
            with c2:
                st.markdown(
                    f"<b style='color:#fff'>{name}</b> {icon}"
                    f"<br><span style='color:#fff;font-weight:600;'>{risk} Risk</span>"
                    f"<br><b style='color:#fff'>Temp:</b> <span style='color:#fff'>{latest['Temperature (°F)']:.1f}°F</span>"
                    f"<br><b style='color:#fff'>Vib:</b> <span style='color:#fff'>{latest['Vibration (g)']:.2f}g</span>"
                    f"<br><b style='color:#fff'>Predicted Failure Risk:</b> <span style='color:#fff'>{fail_risk_percent}%</span>",
                    unsafe_allow_html=True
                )

    # ---- Streamlit-native AI Predictive Alerts Card with "Schedule" Button ----
    ai_alerts = []
    for name in machine_names:
        latest = machine_data[name].iloc[-1]
        risk_percent = predict_failure_risk(
            machine_data[name]["Temperature (°F)"].values,
            machine_data[name]["Vibration (g)"].values
        )
        if risk_percent > 60:  # Only show high-risk machines in AI card
            ai_alerts.append({
                "Machine": name,
                "Risk": risk_percent,
                "Type": "Predicted failure" if latest["Risk"] == "High" else "Caution",
                "Advice": "Schedule inspection immediately" if latest["Risk"] == "High" else "Monitor closely",
                "Status": "Queue" if latest["Risk"] == "High" else "Pending"
            })

    if ai_alerts:
        for alert in ai_alerts:
            card_contents = f"""
            <b style='font-size:1.12em;color:#fff;'>{alert['Machine']}</b>
            <span style='color:#fff;font-weight:600;margin-left:8px;'>
                High failure risk ({alert['Risk']}%)
            </span>
            <span style='float:right;background:#0891b2;color:#fff;padding:3px 16px;border-radius:6px;font-weight:600;'>
                {alert['Status']}
            </span>
            <br>
            <span style='color:#fff;font-size:0.98em;'>Type: {alert['Type']} | {alert['Advice']}</span>
            """
            scheduled = ai_card(card_contents, machine=alert['Machine'], button_key=f"ai_sched_{alert['Machine']}")
            if scheduled:
                st.success(f"✅ Maintenance notified for {alert['Machine']}!")
    else:
        st.markdown(ai_card(
            "<b style='font-size:1.15em;color:#fff;'>🤖 AI Predictive Alerts</b><br><span style='color:#fff;'>No high-risk machines at the moment. ✅</span>"
        ), unsafe_allow_html=True)

    st.markdown("<h4 style='color:white'>Active Alerts</h4>", unsafe_allow_html=True)
    for alert in all_alerts:
        if alert["Severity"] in ["High", "Medium"]:
            acked = st.session_state.ack_log.get(alert['Machine'])
            if acked:
                st.success(f"Acknowledged by {acked} at {alert['Time']}")
            else:
                if st.button(f"Acknowledge {alert['Machine']}", key=f"ack_{alert['Machine']}"):
                    st.session_state.ack_log[alert['Machine']] = role
                    st.session_state.attn_from_operator.add(alert['Machine'])
                    st.success(f"Acknowledged by {role} at {alert['Time']}")

    st.markdown("<h4 style='color:white'>Environmental Data</h4>", unsafe_allow_html=True)
    if env_temp > 80 or env_co2 > 600:
        st.warning("⚠️ Environment out of safe range! Check temperature and air quality.")
    st.info(f"🌡️ {env_temp} °F | 💧 {env_humidity}% | 💨 {env_co2} ppm | Air: {env_air_quality}")

# ========================= MAINTENANCE DASHBOARD =========================
elif role == "Maintenance":
    if st.session_state.attn_from_operator:
        st.warning("⚡ Operator-Acknowledged Alerts: Immediate attention required!")
        for m in st.session_state.attn_from_operator.copy():
            st.write(f"Machine: {m}")
            if st.button(f"Clear Attention: {m}", key=f"clear_attn_{m}"):
                st.session_state.attn_from_operator.remove(m)
        st.markdown("---")
    st.markdown("<h2 style='color:white'>Maintenance Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:white'>High-Risk Machines</h4>", unsafe_allow_html=True)
    high_risk = []
    repaired_now = []
    for name in machine_names:
        latest = machine_data[name].iloc[-1]
        if name in st.session_state.repaired_machines:
            repaired_now.append(name)
        elif latest["Risk"] == "High":
            high_risk.append(name)

    if high_risk:
        grid_cols = st.columns(len(high_risk))
        for i, name in enumerate(high_risk):
            latest = machine_data[name].iloc[-1]
            temp_values = machine_data[name]["Temperature (°F)"].values
            vib_values = machine_data[name]["Vibration (g)"].values
            fail_risk_percent = predict_failure_risk(temp_values, vib_values)
            with grid_cols[i]:
                c1, c2 = st.columns([1.4, 1])
                with c1:
                    st.line_chart(machine_data[name][["Temperature (°F)", "Vibration (g)"]].tail(30), use_container_width=True, height=110)
                with c2:
                    st.markdown(
                        f"<b style='color:#fff;'>{name}</b> 🟥"
                        f"<br><span style='color:#fff;font-weight:600;'>High Risk</span>"
                        f"<br><b style='color:#fff;'>Temp:</b> <span style='color:#fff;'>{latest['Temperature (°F)']:.1f}°F</span>"
                        f"<br><b style='color:#fff;'>Vib:</b> <span style='color:#fff;'>{latest['Vibration (g)']:.2f}g</span>"
                        f"<br><b style='color:#fff;'>Predicted Failure Risk:</b> <span style='color:#fff;'>{fail_risk_percent}%</span>",
                        unsafe_allow_html=True
                    )
                if st.button(f"Mark {name} as Repaired", key=f"fix_{name}"):
                    st.session_state.repaired_machines.add(name)
                    df = st.session_state.maint_df
                    mask = (df["Machine"] == name) & (df["Status"] != "Completed")
                    st.session_state.maint_df.loc[mask, "Status"] = "Completed"
                    if name in st.session_state.attn_from_operator:
                        st.session_state.attn_from_operator.remove(name)
                    st.rerun()
    else:
        st.info("No high-risk machines right now. ✅")

    if repaired_now:
        st.markdown("<h4 style='color:white'>Now Working Normally</h4>", unsafe_allow_html=True)
        grid_cols2 = st.columns(len(repaired_now))
        for i, name in enumerate(repaired_now):
            latest = machine_data[name].iloc[-1]
            temp_values = machine_data[name]["Temperature (°F)"].values
            vib_values = machine_data[name]["Vibration (g)"].values
            fail_risk_percent = predict_failure_risk(temp_values, vib_values)
            with grid_cols2[i]:
                c1, c2 = st.columns([1.4, 1])
                with c1:
                    st.line_chart(machine_data[name][["Temperature (°F)", "Vibration (g)"]].tail(30), use_container_width=True, height=110)
                with c2:
                    st.markdown(
                        f"<b style='color:#fff;'>{name}</b> 🟩"
                        f"<br><span style='color:#fff;font-weight:600;'>Normal</span>"
                        f"<br><b style='color:#fff;'>Temp:</b> <span style='color:#fff;'>{latest['Temperature (°F)']:.1f}°F</span>"
                        f"<br><b style='color:#fff;'>Vib:</b> <span style='color:#fff;'>{latest['Vibration (g)']:.2f}g</span>"
                        f"<br><b style='color:#fff;'>Predicted Failure Risk:</b> <span style='color:#fff;'>{fail_risk_percent}%</span>",
                        unsafe_allow_html=True
                    )

    st.markdown("<h4 style='color:white'>All Alerts</h4>", unsafe_allow_html=True)
    for alert in all_alerts:
        st.info(f"{alert['Machine']}: {alert['Alert']} ({alert['Severity']})")
        if alert['Machine'] not in st.session_state.scheduled_repairs:
            if st.button(f"Schedule Repair: {alert['Machine']}", key=f"repair_{alert['Machine']}"):
                st.session_state.scheduled_repairs.add(alert['Machine'])
                df = st.session_state.maint_df
                mask = (df["Machine"] == alert['Machine']) & (~df["Status"].isin(["Completed", "Scheduled"]))
                if df[mask].empty:
                    new_ticket_number = f"MT-{len(df) + 1:03d}"
                    new_row = {
                        "Ticket #": new_ticket_number,
                        "Machine": alert['Machine'],
                        "Type": "Reactive",
                        "Reason": alert['Alert'],
                        "Created": time.strftime('%Y-%m-%d %H:%M'),
                        "Due": "-",
                        "Assigned To": "-",
                        "Status": "Scheduled"
                    }
                    st.session_state.maint_df = pd.concat([st.session_state.maint_df, pd.DataFrame([new_row])], ignore_index=True)
                else:
                    st.session_state.maint_df.loc[mask, "Status"] = "Scheduled"
                st.success(f"Repair scheduled for {alert['Machine']} (demo only).")
                st.rerun()
        else:
            st.success(f"Repair already scheduled for {alert['Machine']}.")

    st.markdown("<h4 style='color:white'>Maintenance Tickets</h4>", unsafe_allow_html=True)
    st.dataframe(st.session_state.maint_df)
    csv = st.session_state.maint_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Maintenance Tickets (CSV)", csv, "maintenance_tickets.csv", "text/csv")

# ========================= SUPERVISOR DASHBOARD =========================
elif role == "Supervisor":
    st.markdown("<h2 style='color:white'>Supervisor Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:white'>All Machines</h4>", unsafe_allow_html=True)
    grid_cols = st.columns(num_machines)
    for i, name in enumerate(machine_names):
        latest = machine_data[name].iloc[-1]
        risk = latest["Risk"]
        temp_values = machine_data[name]["Temperature (°F)"].values
        vib_values = machine_data[name]["Vibration (g)"].values
        fail_risk_percent = predict_failure_risk(temp_values, vib_values)
        color = "#fff"
        icon = "🟥" if risk == "High" else "🟧" if risk == "Medium" else "🟩"
        with grid_cols[i]:
            c1, c2 = st.columns([1.4, 1])
            with c1:
                st.line_chart(machine_data[name][["Temperature (°F)", "Vibration (g)"]].tail(30), use_container_width=True, height=110)
            with c2:
                st.markdown(
                    f"<b style='color:#fff;'>{name}</b> {icon}"
                    f"<br><span style='color:#fff;font-weight:600;'>{risk} Risk</span>"
                    f"<br><b style='color:#fff;'>Temp:</b> <span style='color:#fff;'>{latest['Temperature (°F)']:.1f}°F</span>"
                    f"<br><b style='color:#fff;'>Vib:</b> <span style='color:#fff;'>{latest['Vibration (g)']:.2f}g</span>"
                    f"<br><b style='color:#fff;'>Predicted Failure Risk:</b> <span style='color:#fff;'>{fail_risk_percent}%</span>",
                    unsafe_allow_html=True
                )
    st.markdown("<h4 style='color:white'>Summary Report</h4>", unsafe_allow_html=True)
    kpi_df = pd.DataFrame({
        "Machine": [m for m in machine_data],
        "Avg Temp": [machine_data[m]["Temperature (°F)"].mean() for m in machine_data],
        "Avg Vib": [machine_data[m]["Vibration (g)"].mean() for m in machine_data],
        "Risk": [machine_data[m]["Risk"].iloc[-1] for m in machine_data]
    })
    st.dataframe(kpi_df)
    csv2 = kpi_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Summary Report (CSV)", csv2, "summary_report.csv", "text/csv")
    st.markdown("<h4 style='color:white'>Approve Maintenance Actions</h4>", unsafe_allow_html=True)
    for idx, row in st.session_state.maint_df.iterrows():
        if row["Status"] == "Queue" and row["Ticket #"] not in st.session_state.approved_tickets:
            if st.button(f"Approve {row['Ticket #']}", key=f"appr_{row['Ticket #']}"):
                st.session_state.approved_tickets.add(row["Ticket #"])
                st.success(f"Ticket {row['Ticket #']} approved!")
        elif row["Ticket #"] in st.session_state.approved_tickets:
            st.info(f"Ticket {row['Ticket #']} already approved.")

st.markdown("---")
with st.expander("📝 Sample Use Cases / User Stories"):
    st.markdown("""
<span style='color:white'>
- <b>As an operator,</b> I want to receive early warnings about potential equipment failure so that I can schedule preventive maintenance.
- <b>As a maintenance engineer,</b> I want to see all high-risk machines and immediately schedule repairs.
- <b>As a supervisor,</b> I want to approve pending maintenance actions and download reports for audit and review.
</span>
""", unsafe_allow_html=True)
st.caption("Smart Predictive Maintenance Demo – Group Project | ISE 2025")
