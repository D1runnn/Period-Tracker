
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go

# --- 1. PRO-LEVEL THEME CONFIG ---
st.set_page_config(page_title="Baby Period Tracker", page_icon="🩸", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }
    
    .status-card {
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        color: white !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .probability-badge {
        background: rgba(255,255,255,0.2);
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA PIPELINE ---
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df.columns = [str(c).strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date']).sort_values(by='Date')

# --- 3. ADVANCED PREDICTION ENGINE ---
today = datetime.now().date()

if len(df) >= 3:
    all_dates = df['Date'].tolist()
    gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
    
    avg_cycle = np.mean(gaps)
    std_dev = np.std(gaps)
    last_start = all_dates[-1].date()
    
    # Prediction Windows
    pred_start_min = last_start + timedelta(days=round(avg_cycle - std_dev))
    pred_start_avg = last_start + timedelta(days=round(avg_cycle))
    pred_start_max = last_start + timedelta(days=round(avg_cycle + std_dev))
    
    # Fertility Logic (The Clinical Curve)
    ovulation_est = pred_start_avg - timedelta(days=14)
    peak_start = ovulation_est - timedelta(days=2)
    peak_end = ovulation_est + timedelta(days=1)
    
    # Current Phase Logic
    days_since = (today - last_start).days
    
    # Probability Logic
    is_fertile = peak_start <= today <= peak_end
    prob_status = "🔴 Low" if not is_fertile else "🟣 PEAK"
    if (ovulation_est - timedelta(days=5)) <= today < peak_start:
        prob_status = "🟡 High"

    # --- UI: HEADER ---
    st.title("🩸 Baby Period Tracker")
    
    # Dynamic Dashboard Card
    phase_colors = {
        "Menstrual": "#E63946", "Follicular": "#2A9D8F", 
        "Ovulatory": "#4361EE", "Luteal": "#F4A261"
    }
    
    if days_since < 5: phase = "Menstrual"
    elif days_since < 13: phase = "Follicular"
    elif days_since < 17: phase = "Ovulatory"
    else: phase = "Luteal"
    
    st.markdown(f"""
        <div class="status-card" style="background: {phase_colors[phase]};">
            <h4 style="margin:0; opacity:0.8;">CURRENT STATUS</h4>
            <h1 style="margin:10px 0;">{phase} Phase (Day {days_since + 1})</h1>
            <div style="display:flex; gap:15px;">
                <span class="probability-badge">Conception Probability: {prob_status}</span>
                <span class="probability-badge">Cycle Stability: {"±" + str(round(std_dev,1)) + "d"}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- UI: PREDICTION TABS ---
    t1, t2, t3 = st.tabs(["🎯 Precision Forecast", "📈 Statistical Ranges", "✍️ Log"])

    with t1:
        st.subheader("Upcoming Milestones")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Next Period (Expected)", pred_start_avg.strftime("%d %b"))
            st.caption(f"Window: {pred_start_min.strftime('%d %b')} - {pred_start_max.strftime('%d %b')}")
        with c2:
            st.metric("Ovulation Day", ovulation_est.strftime("%d %b"))
            st.caption("Most likely date for egg release")
        with c3:
            days_to_ov = (ovulation_est - today).days
            st.metric("Days to Ovulation", f"{days_to_ov}d" if days_to_ov >=0 else "Passed")

    with t2:
        st.subheader("Historical Consistency")
        # Probability Range Visualizer
        fig = go.Figure()
        fig.add_trace(go.Box(x=gaps, name="Cycle Length", boxpoints='all', marker_color='#4361EE'))
        fig.update_layout(title="Variation in Cycle Durations (Days)", template="none")
        st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"**Clinical Insight:** Your cycles range from **{min(gaps)}** to **{max(gaps)}** days. "
                 f"The most frequent duration is **{round(avg_cycle)}** days.")

    with t3:
        with st.form("log_period"):
            log_date = st.date_input("Start Date", today)
            if st.form_submit_button("Sync to Google Sheets"):
                # Standard update logic here
                new_row = pd.DataFrame([{"Date": log_date.strftime("%d/%m/%Y")}])
                updated_df = pd.concat([df[['Date']], new_row], ignore_index=True)
                updated_df['Date'] = pd.to_datetime(updated_df['Date']).dt.strftime("%d/%m/%Y")
                conn.update(data=updated_df)
                st.cache_data.clear()
                st.rerun()

else:
    st.title("🩸 Baby Period Tracker")
    st.info("Please log at least 3 historical dates to unlock probability windows and statistical modeling.")
    # Simple logging form for new users
    with st.form("initial_log"):
        d = st.date_input("Period Start Date", today)
        if st.form_submit_button("Initialize Tracker"):
            pass # Add sync logic
