
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.express as px

# --- 1. THEME-AWARE PRO CSS ---
st.set_page_config(page_title="Luna Pro", page_icon="🩸", layout="wide")

def apply_pro_theme():
    st.markdown("""
        <style>
        /* Modern Typography */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
        
        /* Universal App Styling */
        .stApp { font-family: 'Inter', sans-serif; }
        
        /* Glassmorphic Status Card - Works in Light & Dark */
        .status-card {
            padding: 2rem;
            border-radius: 24px;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            color: white !important;
        }

        /* Metric Box Theme-Aware Borders */
        div[data-testid="stMetric"] {
            background-color: rgba(128, 128, 128, 0.05) !important;
            border: 1px solid rgba(128, 128, 128, 0.2) !important;
            padding: 1.5rem !important;
            border-radius: 16px !important;
        }

        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 10px 24px;
            font-weight: 500;
        }
        
        /* Subheader refinement */
        .stMarkdown h3 { font-weight: 700; letter-spacing: -0.5px; }
        </style>
    """, unsafe_allow_html=True)

apply_pro_theme()

# --- 2. DATA PIPELINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_clean_data():
    df = conn.read(ttl=0)
    if df is not None and not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        return df.dropna(subset=['Date']).sort_values(by='Date')
    return pd.DataFrame(columns=['Date'])

df = load_clean_data()

# --- 3. ANALYTICS ENGINE ---
# Default fallback values
avg_cycle = 28.0
variation = 0.0
days_since_start = 0
today = datetime.now().date()

if len(df) >= 2:
    all_dates = df['Date'].tolist()
    gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
    # Use moving average of last 3 cycles for better accuracy
    avg_cycle = np.mean(gaps[-3:]) if len(gaps) >= 3 else np.mean(gaps)
    variation = np.std(gaps)
    last_date = all_dates[-1].date()
    days_since_start = (today - last_date).days

# --- 4. EXECUTIVE DASHBOARD ---
st.title("🩸 Biological Insights")
st.caption(f"Sync Status: Live | Medical Prediction Engine v2.1")

# Professional Status Logic
if not df.empty:
    # Color Gradients selected for readability in both modes
    if days_since_start < 5:
        phase, color, icon, msg = "Menstrual", "#E63946", "🩸", "Physiological Reset"
    elif days_since_start < 13:
        phase, color, icon, msg = "Follicular", "#2A9D8F", "🌱", "Follicle Maturation"
    elif days_since_start < 17:
        phase, color, icon, msg = "Ovulatory", "#4361EE", "🥚", "Peak Fertility Window"
    else:
        phase, color, icon, msg = "Luteal", "#F4A261", "🌙", "Progesterone Dominance"

    # The Card uses a subtle gradient with the specific phase color
    st.markdown(f"""
        <div class="status-card" style="background: linear-gradient(135deg, {color}CC, {color});">
            <p style="margin:0; text-transform: uppercase; letter-spacing: 1px; font-size: 0.8rem; opacity: 0.8;">Current Biological Phase</p>
            <h1 style="margin:5px 0 15px 0; font-size: 2.8rem;">{icon} {phase}</h1>
            <div style="display: flex; gap: 20px; align-items: center;">
                <span style="background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; font-weight: 600;">Day {days_since_start + 1}</span>
                <span style="opacity: 0.9;">{msg}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Key Performance Indicators
m1, m2, m3, m4 = st.columns(4)
next_period = (df['Date'].max() + timedelta(days=round(avg_cycle))).date() if not df.empty else today
countdown = (next_period - today).days

with m1: st.metric("Predicted Start", next_period.strftime("%b %d"), f"{countdown} days")
with m2: st.metric("Average Cycle", f"{round(avg_cycle, 1)}d")
with m3: st.metric("Cycle Variance", f"±{round(variation, 1)}d")
with m4: 
    # Reliability Score calculation
    score = "High" if variation < 2.5 else "Moderate" if variation < 4.5 else "Low"
    st.metric("Data Reliability", score)

st.write("---")

# --- 5. FUNCTIONAL TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Analytics", "📅 Clinical Forecast", "📝 Action"])

with tab1:
    if len(df) > 1:
        # Theme-aware Charting
        chart_df = pd.DataFrame({"Cycle": range(1, len(gaps)+1), "Days": gaps})
        fig = px.area(chart_df, x="Cycle", y="Days", title="Historical Cycle Consistency")
        fig.update_traces(line_color="#4361EE", fillcolor="rgba(67, 97, 238, 0.2)")
        fig.update_layout(xaxis_title="Past Cycles", yaxis_title="Duration (Days)", template="none")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Historical trends will appear after your second logged entry.")

with tab2:
    st.subheader("Quarterly Outlook")
    st.write("Predicted start dates for the next three cycles:")
    c_a, c_b, c_c = st.columns(3)
    forecast = [c_a, c_b, c_c]
    future_date = next_period
    for i in range(3):
        with forecast[i]:
            st.markdown(f"**Cycle +{i+1}**")
            st.code(future_date.strftime("%A\n%d %B, %Y"))
        future_date += timedelta(days=round(avg_cycle))

with tab3:
    col_l, col_r = st.columns([2, 1])
    with col_l:
        with st.form("log_entry", clear_on_submit=True):
            st.write("#### Add Clinical Data")
            log_date = st.date_input("Period Start Date", today)
            if st.form_submit_button("Submit Entry to Cloud", use_container_width=True):
                # Data formatting & Sync
                new_data = pd.DataFrame([{"Date": log_date.strftime("%d/%m/%Y")}])
                updated = pd.concat([df[['Date']], new_data], ignore_index=True)
                updated['Date'] = pd.to_datetime(updated['Date']).dt.strftime("%d/%m/%Y")
                
                conn.update(data=updated)
                st.cache_data.clear()
                st.rerun()
    with col_r:
        st.write("#### Quick Actions")
        if st.button("🗑️ Remove Last Log"):
            # Logic to drop last row and sync
            pass

# --- 6. HISTORY LOG ---
with st.expander("Detailed Log History"):
    st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True, hide_index=True)
