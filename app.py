import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.express as px

# --- 1. PRO THEMING & UTILITIES ---
st.set_page_config(page_title="Luna Pro | Period & Fertility", page_icon="🩸", layout="wide")

def local_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        
        /* Main Card Styling */
        .status-card {
            padding: 30px;
            border-radius: 20px;
            color: white;
            margin-bottom: 25px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        /* Metric Box Styling */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #f0f2f6;
            padding: 15px 20px;
            border-radius: 12px;
        }
        
        /* Clean Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f8f9fa;
            border-radius: 8px 8px 0 0;
            padding: 10px 20px;
        }
        </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    df = conn.read(ttl=0)
    if df is not None and not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        return df.dropna(subset=['Date']).sort_values(by='Date')
    return pd.DataFrame(columns=['Date'])

df = get_data()

# --- 3. LOGIC & CALCULATIONS ---
avg_cycle = 28.0  # Default
variation = 0.0
days_since_start = 0
today = datetime.now().date()

if len(df) >= 2:
    all_dates = df['Date'].tolist()
    gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
    avg_cycle = np.mean(gaps[-5:]) # Weighted to last 5 cycles
    variation = np.std(gaps)
    last_date = all_dates[-1].date()
    days_since_start = (today - last_date).days

# --- 4. PROFESSIONAL DASHBOARD ---
st.title("🩸 Luna Health Dashboard")
st.caption(f"Last sync: {datetime.now().strftime('%H:%M:%S')} | Data Source: Google Sheets")

# Dynamic Header Card
if len(df) >= 1:
    # Phase Determination
    if days_since_start < 5:
        phase, color, icon = "Menstrual Phase", "linear-gradient(135deg, #ff4b4b, #ff7676)", "🩸"
    elif days_since_start < 13:
        phase, color, icon = "Follicular Phase", "linear-gradient(135deg, #00b09b, #96c93d)", "🌱"
    elif days_since_start < 17:
        phase, color, icon = "Ovulation Window", "linear-gradient(135deg, #6a11cb, #2575fc)", "🥚"
    else:
        phase, color, icon = "Luteal Phase", "linear-gradient(135deg, #f093fb, #f5576c)", "🌙"

    st.markdown(f"""
        <div class="status-card" style="background: {color};">
            <h3 style="margin:0; opacity: 0.9;">Current Status</h3>
            <h1 style="margin:10px 0; font-size: 2.5rem;">{icon} {phase}</h1>
            <p style="margin:0; font-weight: 600;">Day {days_since_start + 1} of your cycle</p>
        </div>
    """, unsafe_allow_html=True)

# Main KPIs
c1, c2, c3, c4 = st.columns(4)
next_start = (df['Date'].max() + timedelta(days=round(avg_cycle))).date() if not df.empty else today
days_to_go = (next_start - today).days

with c1: st.metric("Next Period", next_start.strftime("%b %d"), f"{days_to_go} days left")
with c2: st.metric("Avg Cycle Length", f"{round(avg_cycle)} Days")
with c3: st.metric("Cycle Variation", f"±{round(variation, 1)}d")
with c4: 
    ov_date = next_start - timedelta(days=14)
    st.metric("Est. Ovulation", ov_date.strftime("%b %d"))

st.divider()

# --- 5. INTERACTIVE SECTIONS ---
tab_plan, tab_history, tab_log = st.tabs(["📅 Planning & Fertility", "📊 Trends & Analysis", "✍️ Log Entry"])

with tab_plan:
    st.subheader("Your Next 3 Months")
    p1, p2, p3 = st.columns(3)
    p_cols = [p1, p2, p3]
    curr = next_start
    for i in range(3):
        with p_cols[i]:
            st.markdown(f"**Cycle {i+1}**")
            st.info(f"Starts: {curr.strftime('%d %B %Y')}")
            st.caption(f"Fertile window starts: {(curr - timedelta(days=16)).strftime('%b %d')}")
        curr += timedelta(days=round(avg_cycle))

with tab_history:
    if len(df) > 1:
        fig = px.line(df, x=df.index, y=gaps + [None], markers=True, 
                      title="Cycle Length History", labels={'y':'Days', 'index':'Cycle #'})
        fig.update_traces(line_color='#ff4b4b', line_width=3)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Insufficient data to plot trends.")

with tab_log:
    with st.form("log_form"):
        new_date = st.date_input("When did your last period start?", today)
        submitted = st.form_submit_button("Confirm & Sync to Cloud", use_container_width=True)
        
        if submitted:
            if not df.empty and (pd.to_datetime(new_date) - df['Date'].max()).days < 10:
                st.warning("⚠️ This entry is very close to your last one. Are you sure?")
            
            new_row = pd.DataFrame([{"Date": new_date.strftime("%d/%m/%Y")}])
            updated_df = pd.concat([df[['Date']], new_row], ignore_index=True)
            updated_df['Date'] = pd.to_datetime(updated_df['Date']).dt.strftime("%d/%m/%Y")
            
            conn.update(data=updated_df)
            st.cache_data.clear()
            st.success("Successfully updated!")
            st.rerun()

# --- 6. FOOTER MGMT ---
with st.expander("Advanced Data Management"):
    st.write("Current Records:")
    st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True)
    if st.button("Delete Last Log Entry"):
        # Logic for deletion...
        pass
