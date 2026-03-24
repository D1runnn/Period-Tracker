
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.express as px

# --- 1. PRO-LEVEL THEME CONFIG ---
st.set_page_config(page_title="Baby Period Tracker", page_icon="🩸", layout="wide")

def apply_custom_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        /* Global Font */
        .stApp { font-family: 'Inter', sans-serif; }

        /* Glassmorphic Header Card */
        .main-card {
            padding: 2.5rem;
            border-radius: 24px;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            color: white !important;
        }

        /* Stats Containers */
        div[data-testid="stMetric"] {
            background-color: rgba(128, 128, 128, 0.08) !important;
            border: 1px solid rgba(128, 128, 128, 0.15) !important;
            padding: 1.2rem !important;
            border-radius: 18px !important;
        }

        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] { gap: 12px; }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 25px;
            font-weight: 600;
            border-radius: 10px 10px 0 0;
        }
        </style>
    """, unsafe_allow_html=True)

apply_custom_styles()

# --- 2. DATA PIPELINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def fetch_data():
    df = conn.read(ttl=0)
    if df is not None and not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        return df.dropna(subset=['Date']).sort_values(by='Date')
    return pd.DataFrame(columns=['Date'])

df = fetch_data()

# --- 3. ANALYTICS ENGINE ---
today = datetime.now().date()
avg_cycle = 28.0
variation = 0.0
cycle_gaps = []
status_msg = "Awaiting more data..."

if len(df) >= 2:
    all_dates = df['Date'].tolist()
    cycle_gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
    
    # Advanced Stats
    avg_cycle = np.mean(cycle_gaps[-4:]) if len(cycle_gaps) >= 4 else np.mean(cycle_gaps)
    variation = np.std(cycle_gaps)
    last_start = all_dates[-1].date()
    days_in = (today - last_start).days
    
    # Logic for Consistency Score
    if variation < 2: regularity = "High (Clinical Grade)"
    elif variation < 4: regularity = "Normal / Stable"
    else: regularity = "Irregular / High Variance"
else:
    days_in = 0
    regularity = "Initial Baseline"

# --- 4. TOP INTERFACE ---
st.title("🩸 Baby Period Tracker")
st.caption("Advanced Menstrual Health Analytics • Powered by Google Sheets")

if not df.empty:
    # Phase Logic & Visuals
    if days_in < 5:
        p_name, p_col, p_icon = "Menstrual Phase", "#E63946", "🩸"
    elif days_in < 13:
        p_name, p_col, p_icon = "Follicular Phase", "#2A9D8F", "🌱"
    elif days_in < 17:
        p_name, p_col, p_icon = "Ovulation Window", "#4361EE", "🥚"
    else:
        p_name, p_col, p_icon = "Luteal Phase", "#F4A261", "🌙"

    st.markdown(f"""
        <div class="main-card" style="background: linear-gradient(135deg, {p_col}DD, {p_col});">
            <p style="margin:0; opacity: 0.8; text-transform: uppercase; font-size: 0.75rem; font-weight: 700;">Current Biological Status</p>
            <h1 style="margin:5px 0 15px 0; font-size: 2.5rem;">{p_icon} {p_name}</h1>
            <div style="display: flex; gap: 15px; align-items: center;">
                <span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 30px; font-weight: 600;">Cycle Day {days_in + 1}</span>
                <span style="opacity: 0.9;">Typical {round(avg_cycle)}-day rhythm detected.</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# KPI Dashboard
m1, m2, m3, m4 = st.columns(4)
next_due = (df['Date'].max() + timedelta(days=round(avg_cycle))).date() if not df.empty else today
countdown = (next_due - today).days

with m1: st.metric("Predicted Start", next_due.strftime("%d %b"), f"{countdown}d left")
with m2: st.metric("Average Cycle", f"{round(avg_cycle, 1)}d")
with m3: st.metric("Consistency", regularity)
with m4: 
    ov_date = next_due - timedelta(days=14)
    st.metric("Fertility Peak", ov_date.strftime("%d %b"))

st.write("---")

# --- 5. FUNCTIONAL TABS ---
tab_trends, tab_forecast, tab_log = st.tabs(["📊 Data Insights", "📅 90-Day Forecast", "✍️ Log Entry"])

with tab_trends:
    if len(cycle_gaps) > 0:
        c_left, c_right = st.columns([2, 1])
        with c_left:
            chart_df = pd.DataFrame({"Index": range(1, len(cycle_gaps)+1), "Days": cycle_gaps})
            fig = px.area(chart_df, x="Index", y="Days", title="Clinical Cycle History")
            fig.update_traces(line_color="#4361EE", fillcolor="rgba(67, 97, 238, 0.1)")
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", yaxis_range=[20, 45])
            st.plotly_chart(fig, use_container_width=True)
        with c_right:
            st.write("#### Statistical Range")
            st.info(f"**Shortest Cycle:** {min(cycle_gaps)} days")
            st.info(f"**Longest Cycle:** {max(cycle_gaps)} days")
            st.caption("Standardizing your data helps refine fertility window accuracy.")
    else:
        st.info("Log multiple periods to generate consistency charts.")

with tab_forecast:
    st.write("#### Projected Biological Milestones")
    f1, f2, f3 = st.columns(3)
    f_cols = [f1, f2, f3]
    future_ptr = next_due
    for i in range(3):
        with f_cols[i]:
            st.markdown(f"**Cycle {i+1} Forecast**")
            st.success(f"Start: {future_ptr.strftime('%B %d')}")
            st.caption(f"Estimated Ovulation: {(future_ptr + timedelta(days=round(avg_cycle/2))).strftime('%b %d')}")
        future_ptr += timedelta(days=round(avg_cycle))

with tab_log:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        with st.form("new_entry", clear_on_submit=True):
            st.write("#### Record New Period")
            new_date = st.date_input("Start Date", today)
            if st.form_submit_button("Sync Entry to Cloud", use_container_width=True):
                if not df.empty and (pd.to_datetime(new_date) - df['Date'].max()).days < 10:
                    st.error("Entry rejected: Date is too close to the last recorded period.")
                else:
                    new_row = pd.DataFrame([{"Date": new_date.strftime("%d/%m/%Y")}])
                    updated_df = pd.concat([df[['Date']], new_row], ignore_index=True)
                    updated_df['Date'] = pd.to_datetime(updated_df['Date']).dt.strftime("%d/%m/%Y")
                    conn.update(data=updated_df)
                    st.cache_data.clear()
                    st.rerun()
    with col_b:
        st.write("#### History Management")
        if st.button("🗑️ Delete Last Entry"):
            if not df.empty:
                updated_df = df.iloc[:-1]
                updated_df['Date'] = updated_df['Date'].dt.strftime("%d/%m/%Y")
                conn.update(data=updated_df)
                st.cache_data.clear()
                st.rerun()

# --- 6. RAW DATA (Medical Record) ---
with st.expander("Full Medical History (Read-Only)"):
    if not df.empty:
        st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True, hide_index=True)
