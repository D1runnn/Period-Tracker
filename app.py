
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.express as px

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Luna Period Tracker", page_icon="🌙", layout="centered")

# Custom CSS for a "Mobile App" look
st.markdown("""
    <style>
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #f0f2f6;
    }
    .main { background-color: #fcfcfd; }
    div[data-testid="stExpander"] { border-radius: 15px; }
    </style>
""", unsafe_allow_index=True)

# --- 2. SETUP CONNECTION & DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl=0)
    if not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date']).sort_values(by='Date')
    return df

df = load_data()

# --- 3. SIDEBAR SETTINGS ---
with st.sidebar:
    st.title("⚙️ App Settings")
    default_period_len = st.slider("Average Period Length", 3, 10, 5)
    st.divider()
    st.info("This app uses your start dates to predict future cycles and fertility windows.")

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
    
    # Fallback if data is sparse
    if len(valid_gaps) < 2:
        valid_gaps = [g for g in cycle_gaps if 15 < g < 50]

    if valid_gaps:
        # Weighted Average (Prioritize recent cycles)
        weights = np.ones(len(valid_gaps))
        if len(weights) >= 3: weights[-3:] = 2.0 
        avg_cycle = np.average(valid_gaps, weights=weights)
        variation = min(np.std(valid_gaps), 5) if len(valid_gaps) > 1 else 2
        
        last_date = all_dates[-1].date()
        days_since_start = (today - last_date).days
        
        # --- TOP METRICS DASHBOARD ---
        col1, col2, col3 = st.columns(3)
        
        # Countdown Logic
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
            phase, icon, color, tip = "Menstrual Phase", "🩸", "#FF4B4B", "Rest and hydrate."
        elif days_since_start < 12:
            phase, icon, color, tip = "Follicular Phase", "🌱", "#00CC96", "Energy levels are rising!"
        elif days_since_start < 16:
            phase, icon, color, tip = "Ovulation Window", "🥚", "#636EFA", "Peak fertility window."
        else:
            phase, icon, color, tip = "Luteal Phase", "🌙", "#FFA15A", "Pms might start soon."

        progress_val = min(max(days_since_start / avg_cycle, 0.0), 1.0)
        st.progress(progress_val)
        st.markdown(f"**{icon} {phase}** — Day {days_since_start + 1}")
        st.caption(f"💡 {tip}")

        # --- TABS FOR PREDICTIONS ---
        st.divider()
        tab1, tab2, tab3 = st.tabs(["📅 3-Month Forecast", "🌟 Fertility Window", "📊 Trends"])

        with tab1:
            st.markdown("#### Projected Start Dates")
            forecast_dates = []
            curr_projected = last_date
            for i in range(3):
                curr_projected = curr_projected + timedelta(days=round(avg_cycle))
                forecast_dates.append(curr_projected)
            
            f_col1, f_col2, f_col3 = st.columns(3)
            cols = [f_col1, f_col2, f_col3]
            for i, d in enumerate(forecast_dates):
                cols[i].success(f"**{d.strftime('%b %d')}**")
                cols[i].caption(f"Cycle {i+1}")

        with tab2:
            # Re-calculate fertility for the upcoming cycle
            ovulation_day = next_period_start - timedelta(days=14)
            fert_start = ovulation_day - timedelta(days=5)
            fert_end = ovulation_day + timedelta(days=1)
            
            st.info(f"### {fert_start.strftime('%d %b')} – {fert_end.strftime('%d %b')}")
            st.write(f"Estimated Ovulation: **{ovulation_day.strftime('%d %b')}**")
            st.caption("Note: This is an estimate based on your average cycle length.")

        with tab3:
            chart_data = pd.DataFrame({
                "Date": all_dates[1:],
                "Length": cycle_gaps
            })
            fig = px.area(chart_data, x="Date", y="Length", title="Cycle History")
            fig.add_hline(y=avg_cycle, line_dash="dot", annotation_text="Average")
            fig.update_layout(yaxis_range=[20, 45], plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Collecting more data to provide accurate variations...")

elif df.empty:
    st.warning("Welcome! Please log your first period below to get started.")
else:
    st.info("Log one more period to unlock predictions and trends!")

# --- 5. LOGGING SECTION ---
st.divider()
st.subheader("Add New Data")
with st.container():
    new_date = st.date_input("Start Date of Period", value=today)
    log_btn = st.button("Log Start Date", use_container_width=True, type="primary")

    if log_btn:
        # Validation: prevent double logging within 10 days
        if not df.empty and (pd.to_datetime(new_date) - df['Date'].max()).days < 10:
            st.error("This date is too close to your last log!")
        else:
            new_entry = pd.DataFrame([{"Date": new_date.strftime("%d/%m/%Y")}])
            updated_df = pd.concat([df[['Date']], new_entry], ignore_index=True)
            updated_df['Date'] = pd.to_datetime(updated_df['Date']).dt.strftime("%d/%m/%Y")
            
            conn.update(data=updated_df)
            st.cache_data.clear()
            st.success("Logged successfully!")
            st.rerun()

# --- 6. DATA MANAGEMENT ---
with st.expander("Manage History"):
    if not df.empty:
        # Show table of past dates
        history = df.sort_values(by='Date', ascending=False).copy()
        history['Date'] = history['Date'].dt.strftime('%B %d, %Y')
        st.dataframe(history, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Delete Most Recent Entry"):
            updated_df = df.sort_values(by='Date').iloc[:-1]
            updated_df['Date'] = updated_df['Date'].dt.strftime("%d/%m/%Y")
            conn.update(data=updated_df)
            st.cache_data.clear()
            st.rerun()
