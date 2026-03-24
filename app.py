
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.express as px

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Luna Period Tracker", page_icon="🌙", layout="centered")

# Custom CSS for a "Mobile App" look
# Note: fixed the 'unsafe_allow_html' parameter here
st.markdown("""
    <style>
    .stMetric {
        background-color: #ffffff !important;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        border: 1px solid #f0f2f6 !important;
    }
    .main { background-color: #fcfcfd; }
    div[data-testid="stExpander"] { border-radius: 15px; }
    
    /* Style the tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 10px 10px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF4B4B;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. SETUP CONNECTION & DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            # Handle date parsing safely
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Date']).sort_values(by='Date')
            return df
        return pd.DataFrame(columns=['Date'])
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame(columns=['Date'])

df = load_data()

# --- 3. SIDEBAR SETTINGS ---
with st.sidebar:
    st.title("⚙️ App Settings")
    default_period_len = st.slider("Average Period Length", 3, 10, 5)
    st.divider()
    st.info("Predictions are based on your logged start dates.")

# --- 4. HEADER ---
st.title("🌙 Luna Tracker")
today = datetime.now().date()

if not df.empty and len(df) >= 2:
    all_dates = df['Date'].tolist()
    
    # --- CALCULATION ENGINE ---
    cycle_gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
    series_gaps = pd.Series(cycle_gaps)
    
    # Remove Outliers (IQR Method)
    q1, q3 = series_gaps.quantile(0.25), series_gaps.quantile(0.75)
    iqr = q3 - q1
    valid_gaps = series_gaps[(series_gaps >= q1 - 1.5 * iqr) & (series_gaps <= q3 + 1.5 * iqr)].tolist()
    
    if len(valid_gaps) < 1:
        valid_gaps = [g for g in cycle_gaps if 15 < g < 50]

    if valid_gaps:
        # Weighted Average
        weights = np.ones(len(valid_gaps))
        if len(weights) >= 3: weights[-3:] = 2.0 
        avg_cycle = np.average(valid_gaps, weights=weights)
        variation = min(np.std(valid_gaps), 5) if len(valid_gaps) > 1 else 2
        
        last_date = all_dates[-1].date()
        days_since_start = (today - last_date).days
        
        # --- TOP METRICS ---
        col1, col2, col3 = st.columns(3)
        next_period_start = last_date + timedelta(days=round(avg_cycle))
        days_until = (next_period_start - today).days
        
        with col1:
            if days_until > 0:
                st.metric("Next Period", f"{days_until} Days", "Remaining")
            elif days_until == 0:
                st.metric("Next Period", "Today!", delta="Due", delta_color="inverse")
            else:
                st.metric("Next Period", f"{abs(days_until)}d Late", delta_color="inverse")
        
        with col2:
            st.metric("Avg Cycle", f"{round(avg_cycle)} Days")
        
        with col3:
            status = "Regular" if variation < 3 else "Irregular"
            st.metric("Stability", status, f"±{round(variation, 1)}d")

        # --- PHASE VISUALIZER ---
        st.subheader("Current Phase")
        if days_since_start < default_period_len:
            phase, icon, tip = "Menstrual Phase", "🩸", "Rest and hydrate. Your body is resetting."
        elif days_since_start < 12:
            phase, icon, tip = "Follicular Phase", "🌱", "Energy levels are rising! Great time for workouts."
        elif days_since_start < 16:
            phase, icon, tip = "Ovulation Window", "🥚", "You are in your peak fertility window."
        else:
            phase, icon, tip = "Luteal Phase", "🌙", "Progesterone is high. You might feel more introverted."

        progress_val = min(max(days_since_start / avg_cycle, 0.0), 1.0)
        st.progress(progress_val)
        st.markdown(f"**{icon} {phase}** — Day {days_since_start + 1}")
        st.caption(f"💡 {tip}")

        # --- TABS ---
        st.divider()
        tab1, tab2, tab3 = st.tabs(["📅 3-Month Forecast", "🌟 Fertility", "📊 History"])

        with tab1:
            st.markdown("#### Future Predicted Starts")
            f_col1, f_col2, f_col3 = st.columns(3)
            cols = [f_col1, f_col2, f_col3]
            curr_proj = last_date
            for i in range(3):
                curr_proj = curr_proj + timedelta(days=round(avg_cycle))
                cols[i].success(f"**{curr_proj.strftime('%b %d')}**")
                cols[i].caption(f"Cycle {i+1}")

        with tab2:
            ovulation_day = next_period_start - timedelta(days=14)
            fert_start = ovulation_day - timedelta(days=5)
            fert_end = ovulation_day + timedelta(days=1)
            st.info(f"### {fert_start.strftime('%d %b')} – {fert_end.strftime('%d %b')}")
            st.write(f"Estimated Ovulation: **{ovulation_day.strftime('%d %b')}**")

        with tab3:
            chart_df = pd.DataFrame({"Date": all_dates[1:], "Length": cycle_gaps})
            fig = px.area(chart_df, x="Date", y="Length", title="Cycle History")
            fig.update_layout(yaxis_range=[20, 45], plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Log another period to calculate variations.")

elif df.empty:
    st.warning("No data found. Log your first start date below.")
else:
    st.info("Almost there! Log your next period to unlock insights.")

# --- 5. LOGGING ---
st.divider()
st.subheader("Log Actual Start Date")
new_date = st.date_input("Start Date", value=today)

if st.button("Log to Cloud", use_container_width=True, type="primary"):
    # Guard against double entries
    if not df.empty and (pd.to_datetime(new_date) - df['Date'].max()).days < 10:
        st.error("Error: This date is too close to your last entry.")
    else:
        new_row = pd.DataFrame([{"Date": new_date.strftime("%d/%m/%Y")}])
        # Force column consistency
        final_df = pd.concat([df[['Date']], new_row], ignore_index=True)
        # Convert back to string for GSheets update
        final_df['Date'] = pd.to_datetime(final_df['Date']).dt.strftime("%d/%m/%Y")
        
        conn.update(data=final_df)
        st.cache_data.clear()
        st.success("Synced with Google Sheets!")
        st.rerun()

# --- 6. MANAGEMENT ---
with st.expander("Manage Records"):
    if not df.empty:
        history_display = df.sort_values(by='Date', ascending=False).copy()
        history_display['Date'] = history_display['Date'].dt.strftime('%B %d, %Y')
        st.dataframe(history_display, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Delete Last Entry"):
            updated = df.sort_values(by='Date').iloc[:-1]
            updated['Date'] = updated['Date'].dt.strftime("%d/%m/%Y")
            conn.update(data=updated)
            st.cache_data.clear()
            st.rerun()
