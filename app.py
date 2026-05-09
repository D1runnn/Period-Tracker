import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- 1. UI ENGINEERING: THEME-AWARE CONFIG & CSS ---
st.set_page_config(page_title="Baby Period Tracker", page_icon="🩸", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { font-family: 'Inter', sans-serif; }
    
    div[data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 1.25rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
    }

    .status-card {
        padding: 2rem;
        border-radius: 16px;
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-left: 8px solid;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
        background-color: rgba(128, 128, 128, 0.15);
        margin-right: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA PIPELINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10) # Reduced TTL for faster updates
def get_data():
    try:
        # Read data and force date parsing strictly as DD/MM/YYYY
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            # Crucial: Specify format and dayfirst to prevent MM/DD flipping
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, format='%d/%m/%Y', errors='coerce')
            return df.dropna(subset=['Date']).sort_values(by='Date')
    except Exception as e:
        st.error(f"Database connection error: {e}")
    return pd.DataFrame(columns=['Date'])

df = get_data()

# --- 3. ANALYTICS ENGINE ---
today = datetime.now().date()

st.title("🩸 Baby Period Tracker")
st.caption("Clinical Menstrual Health & Fertility Dashboard")

if len(df) >= 3:
    all_dates = df['Date'].tolist()
    gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
    
    avg_cycle = np.mean(gaps)
    std_dev = np.std(gaps)
    last_start = all_dates[-1].date()
    days_since = (today - last_start).days
    
    pred_start_avg = last_start + timedelta(days=round(avg_cycle))
    pred_start_min = pred_start_avg - timedelta(days=round(std_dev))
    pred_start_max = pred_start_avg + timedelta(days=round(std_dev))
    
    ovulation_est = pred_start_avg - timedelta(days=14)
    peak_fertility_start = ovulation_est - timedelta(days=2)
    peak_fertility_end = ovulation_est + timedelta(days=1)
    
    if days_since < 5:
        phase, color, msg = "Menstrual Phase", "#FF4B4B", "Rest and recover."
    elif days_since < 13:
        phase, color, msg = "Follicular Phase", "#00CC96", "Estrogen rising."
    elif days_since < 17:
        phase, color, msg = "Ovulatory Phase", "#636EFA", "Peak fertility window."
    else:
        phase, color, msg = "Luteal Phase", "#FFA15A", "Progesterone dominant."

    days_to_ov = (ovulation_est - today).days
    if peak_fertility_start <= today <= peak_fertility_end:
        prob_status, prob_icon = "Peak", "🌟"
    elif (ovulation_est - timedelta(days=5)) <= today < peak_fertility_start:
        prob_status, prob_icon = "High", "📈"
    else:
        prob_status, prob_icon = "Low", "📉"

    st.markdown(f"""
        <div class="status-card" style="border-left-color: {color};">
            <h4 style="margin-top: 0; margin-bottom: 0.5rem; color: var(--text-color); opacity: 0.7; font-weight: 500;">CURRENT BIOLOGICAL STATUS</h4>
            <h1 style="margin-top: 0; margin-bottom: 1rem; color: {color};">{phase}</h1>
            <div>
                <span class="status-badge">Day {days_since + 1} of Cycle</span>
                <span class="status-badge">{prob_icon} Fertility: {prob_status}</span>
                <span class="status-badge">±{round(std_dev, 1)}d Variance</span>
            </div>
            <p style="margin-top: 1rem; margin-bottom: 0; font-size: 0.95rem; opacity: 0.8;">{msg}</p>
        </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Next Period", pred_start_avg.strftime("%b %d"), f"{(pred_start_avg - today).days} days away")
    with m2:
        st.metric("Ovulation Est.", ovulation_est.strftime("%b %d"), prob_status)
    with m3:
        st.metric("Average Length", f"{round(avg_cycle)} Days")
    with m4:
        st.metric("Prediction Window", f"{pred_start_min.strftime('%d')} - {pred_start_max.strftime('%d %b')}")

    st.write("---")

    tab_overview, tab_history, tab_log = st.tabs(["🔄 Cycle Overview", "📊 Historical Trends", "✍️ Log Data"])

    with tab_overview:
        col_chart, col_forecast = st.columns([1.5, 1])
        with col_chart:
            mens_days, fert_days = 5, 6
            foll_days = max((ovulation_est - last_start).days - 5, 1)
            lut_days = max(round(avg_cycle) - mens_days - foll_days - fert_days, 1)
            
            fig_wheel = go.Figure(data=[go.Pie(
                labels=['Menstrual', 'Follicular', 'Fertile', 'Luteal'], 
                values=[mens_days, foll_days, fert_days, lut_days], 
                hole=0.7,
                marker_colors=['#FF4B4B', '#00CC96', '#636EFA', '#FFA15A'],
                textinfo='none',
                hoverinfo='label+value'
            )])
            fig_wheel.update_layout(showlegend=True, margin=dict(t=40, b=0, l=0, r=0), height=350, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_wheel, use_container_width=True, theme="streamlit")

        with col_forecast:
            st.write("#### 📅 Upcoming Milestones")
            st.info(f"**Fertile Window Begins:**\n{(ovulation_est - timedelta(days=5)).strftime('%A, %B %d')}")
            st.success(f"**Peak Ovulation:**\n{ovulation_est.strftime('%A, %B %d')}")
            st.error(f"**Next Period Window:**\n{pred_start_min.strftime('%b %d')} to {pred_start_max.strftime('%b %d')}")

    with tab_history:
        st.write("#### Cycle Variance Analysis")
        colors = ["#00CC96" if (avg_cycle - std_dev) <= g <= (avg_cycle + std_dev) else "#FF4B4B" for g in gaps]
        fig_bar = go.Figure(data=[go.Bar(x=[f"Cycle {i+1}" for i in range(len(gaps))], y=gaps, marker_color=colors, text=gaps, textposition='auto')])
        fig_bar.add_hline(y=avg_cycle, line_dash="dash", line_color="#888", annotation_text="Average")
        fig_bar.update_layout(yaxis_title="Duration (Days)", height=350, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")

    with tab_log:
        col_form, col_manage = st.columns([2, 1])
        with col_form:
            with st.form("log_form", clear_on_submit=True):
                st.write("#### Log New Cycle Start")
                log_date = st.date_input("Start Date", today)
                if st.form_submit_button("Save to Google Sheets", use_container_width=True):
                    # Create new row and ensure all dates are converted to strings in the same format
                    new_row = pd.DataFrame([{"Date": log_date.strftime("%d/%m/%Y")}])
                    current_dates = df[['Date']].copy()
                    current_dates['Date'] = current_dates['Date'].dt.strftime("%d/%m/%Y")
                    updated_df = pd.concat([current_dates, new_row], ignore_index=True)
                    
                    conn.update(data=updated_df)
                    st.cache_data.clear()
                    st.rerun()
        
        with col_manage:
            st.write("#### Data Management")
            if st.button("🗑️ Undo Last Log", use_container_width=True):
                if not df.empty:
                    updated_df = df.iloc[:-1].copy()
                    updated_df['Date'] = updated_df['Date'].dt.strftime("%d/%m/%Y")
                    conn.update(data=updated_df)
                    st.cache_data.clear()
                    st.rerun()
            with st.expander("View Raw Data"):
                st.dataframe(df.sort_values(by='Date', ascending=False), hide_index=True, use_container_width=True)

else:
    st.info("👋 Welcome! Please log at least 3 previous cycle start dates.")
    with st.form("initial_log"):
        d = st.date_input("Period Start Date", today)
        if st.form_submit_button("Log Initial Date"):
            new_row = pd.DataFrame([{"Date": d.strftime("%d/%m/%Y")}])
            conn.update(data=new_row)
            st.cache_data.clear()
            st.rerun()
