import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- 1. PRO-LEVEL THEME CONFIG ---
st.set_page_config(page_title="Baby Period Tracker", page_icon="🩸", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }
    
    /* Subtle container styling */
    div[data-testid="stMetric"] {
        background-color: #f8f9fa !important;
        border: 1px solid #e9ecef !important;
        padding: 1.5rem !important;
        border-radius: 16px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA PIPELINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def get_data():
    df = conn.read(ttl=0)
    if df is not None and not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        return df.dropna(subset=['Date']).sort_values(by='Date')
    return pd.DataFrame(columns=['Date'])

df = get_data()

# --- 3. CORE ENGINE ---
today = datetime.now().date()

st.title("🩸 Baby Period Tracker")
st.caption("Clinical Menstrual Health & Fertility Visualization")

if len(df) >= 3:
    all_dates = df['Date'].tolist()
    gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
    
    avg_cycle = np.mean(gaps)
    std_dev = np.std(gaps)
    last_start = all_dates[-1].date()
    days_since = (today - last_start).days
    
    pred_start = last_start + timedelta(days=round(avg_cycle))
    ovulation_est = pred_start - timedelta(days=14)
    
    # --- VISUALIZATION 1: THE CYCLE WHEEL ---
    st.subheader("Your Current Cycle")
    
    # Calculate proportional days for the chart
    mens_days = 5
    foll_days = max(ovulation_est - last_start - timedelta(days=7), timedelta(days=1)).days
    fert_days = 6 # 5 days before + ovulation day
    lut_days = max(round(avg_cycle) - mens_days - foll_days - fert_days, 10)
    
    phases = ['Menstrual', 'Follicular', 'Fertile Window', 'Luteal']
    durations = [mens_days, foll_days, fert_days, lut_days]
    colors = ['#E63946', '#2A9D8F', '#4361EE', '#F4A261']
    
    col_wheel, col_metrics = st.columns([1.5, 1])
    
    with col_wheel:
        fig_wheel = go.Figure(data=[go.Pie(
            labels=phases, 
            values=durations, 
            hole=0.75,
            marker_colors=colors,
            textinfo='label',
            textposition='outside',
            hoverinfo='label+value',
            direction='clockwise',
            sort=False
        )])
        
        # Add center text for current day
        fig_wheel.update_layout(
            annotations=[dict(text=f"Day<br>{days_since + 1}", x=0.5, y=0.5, font_size=36, showarrow=False)],
            showlegend=False,
            margin=dict(t=20, b=20, l=20, r=20),
            height=350
        )
        st.plotly_chart(fig_wheel, use_container_width=True)

    with col_metrics:
        # --- VISUALIZATION 2: FERTILITY GAUGE ---
        days_to_ov = (ovulation_est - today).days
        prob_score = 10 if days_to_ov in [0, 1] else (8 if 2 <= days_to_ov <= 5 else 2)
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge",
            value = prob_score,
            title = {'text': "Conception Probability", 'font': {'size': 18}},
            gauge = {
                'axis': {'range': [0, 10], 'visible': False},
                'bar': {'color': "#4361EE" if prob_score > 5 else "#d3d3d3"},
                'steps': [
                    {'range': [0, 4], 'color': "#f8f9fa"},
                    {'range': [4, 8], 'color': "#e9ecef"},
                    {'range': [8, 10], 'color': "#dee2e6"}
                ],
            }
        ))
        fig_gauge.update_layout(height=200, margin=dict(t=40, b=10, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Quick summary metrics underneath
        st.metric("Next Period", pred_start.strftime("%d %B"), f"±{round(std_dev)} days")
        st.metric("Expected Ovulation", ovulation_est.strftime("%d %B"))

    st.divider()

    # --- VISUALIZATION 3: CYCLE HISTORY BAR CHART ---
    tab_history, tab_forecast, tab_log = st.tabs(["📊 Cycle Variance", "📅 Forecast", "✍️ Log Entry"])
    
    with tab_history:
        st.write("#### Historical Cycle Durations")
        # Color bars based on whether they fall inside the "normal" range
        bar_colors = ["#2A9D8F" if (avg_cycle - 3) <= gap <= (avg_cycle + 3) else "#E63946" for gap in gaps]
        
        fig_bar = go.Figure(data=[go.Bar(
            x=[f"Cycle {i+1}" for i in range(len(gaps))],
            y=gaps,
            marker_color=bar_colors,
            text=gaps,
            textposition='auto'
        )])
        
        # Add a horizontal line for the average
        fig_bar.add_hline(y=avg_cycle, line_dash="dot", line_color="#333", annotation_text="Your Average")
        fig_bar.update_layout(yaxis_title="Days", template="none", height=300)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption("🟢 Normal Range | 🔴 High Variance (Outlier)")

    with tab_forecast:
        st.write("#### 90-Day Biological Outlook")
        f1, f2, f3 = st.columns(3)
        future_ptr = pred_start
        for i, col in enumerate([f1, f2, f3]):
            with col:
                st.success(f"**Cycle +{i+1}:** {future_ptr.strftime('%d %B %Y')}")
                st.caption(f"Fertile Window starts ~{(future_ptr - timedelta(days=19)).strftime('%d %b')}")
            future_ptr += timedelta(days=round(avg_cycle))

    with tab_log:
        with st.form("log_period", clear_on_submit=True):
            log_date = st.date_input("Start Date of Last Period", today)
            if st.form_submit_button("Securely Sync Data", use_container_width=True):
                new_row = pd.DataFrame([{"Date": log_date.strftime("%d/%m/%Y")}])
                updated_df = pd.concat([df[['Date']], new_row], ignore_index=True)
                updated_df['Date'] = pd.to_datetime(updated_df['Date']).dt.strftime("%d/%m/%Y")
                conn.update(data=updated_df)
                st.cache_data.clear()
                st.rerun()

else:
    st.info("Log at least 3 cycle start dates to generate the Clinical Visualizations.")
    with st.form("initial_log"):
        d = st.date_input("Period Start Date", today)
        if st.form_submit_button("Log Date"):
            new_row = pd.DataFrame([{"Date": d.strftime("%d/%m/%Y")}])
            updated_df = pd.concat([df[['Date']], new_row], ignore_index=True) if not df.empty else new_row
            updated_df['Date'] = pd.to_datetime(updated_df['Date']).dt.strftime("%d/%m/%Y")
            conn.update(data=updated_df)
            st.cache_data.clear()
            st.rerun()

with st.expander("Raw Data Management"):
    if not df.empty:
        st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True, hide_index=True)
        if st.button("Delete Most Recent Entry"):
            updated_df = df.iloc[:-1]
            updated_df['Date'] = updated_df['Date'].dt.strftime("%d/%m/%Y")
            conn.update(data=updated_df)
            st.cache_data.clear()
            st.rerun()
