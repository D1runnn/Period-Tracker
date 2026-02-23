
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.express as px  # New import for charting

# 1. Page Configuration
st.set_page_config(page_title="Baby Period Tracker🩸", page_icon="🩸", layout="centered")

# 2. Setup Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Fetch and Clean Data
df = conn.read(ttl=0)

st.title("🩸 Baby Period Tracker")

if not df.empty:
    df.columns = [str(c).strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date']).sort_values(by='Date')
    all_dates = df['Date'].tolist()

    if len(all_dates) >= 2:
        # --- CALCULATION ENGINE ---
        cycle_gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
        series_gaps = pd.Series(cycle_gaps)
        
        # Remove Outliers
        q1, q3 = series_gaps.quantile(0.25), series_gaps.quantile(0.75)
        iqr = q3 - q1
        valid_gaps = series_gaps[(series_gaps >= q1 - 1.5 * iqr) & (series_gaps <= q3 + 1.5 * iqr)].tolist()
        
        if len(valid_gaps) < 2:
            valid_gaps = [g for g in cycle_gaps if 15 < g < 50]

        if valid_gaps:
            # Weighted Average
            weights = np.ones(len(valid_gaps))
            if len(weights) >= 3: weights[-3:] = 2.0 
            
            avg_cycle = np.average(valid_gaps, weights=weights)
            variation = min(np.std(valid_gaps), 4) if len(valid_gaps) > 1 else 2
            
            last_date = all_dates[-1]
            pred_start = last_date + timedelta(days=round(avg_cycle))
            
            # Fertility Logic
            ovulation_day = pred_start - timedelta(days=14)
            fertile_start = ovulation_day - timedelta(days=5)
            fertile_end = ovulation_day + timedelta(days=1)

            # --- UI: TOP METRICS ---
            days_until = (pred_start.date() - datetime.now().date()).days
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if days_until > 0:
                    st.metric("Countdown", f"{days_until} Days", "Remaining")
                elif days_until == 0:
                    st.metric("Countdown", "Today!", delta="Due", delta_color="inverse")
                else:
                    st.metric("Countdown", f"{abs(days_until)} Days", "Late", delta_color="inverse")
            
            col_b.metric("Avg Cycle", f"{round(avg_cycle, 1)}d")
            col_c.metric("Variation", f"±{round(variation, 1)}d")

            # --- UI: PHASE VISUALIZER ---
            st.subheader("Current Cycle Phase")
            days_since_start = (datetime.now().date() - last_date.date()).days
            
            if days_since_start <= 5:
                phase, color, icon = "Menstrual Phase", "#FF4B4B", "🩸"
            elif days_since_start <= 13:
                phase, color, icon = "Follicular Phase", "#00CC96", "🌱"
            elif days_since_start <= 16:
                phase, color, icon = "Ovulation Window", "#636EFA", "🥚"
            else:
                phase, color, icon = "Luteal Phase", "#FFA15A", "🌙"
            
            progress_val = min(days_since_start / round(avg_cycle), 1.0)
            st.progress(progress_val)
            st.markdown(f"Current: **{icon} {phase}** (Day {days_since_start+1})")

            # --- UI: PREDICTIONS ---
            st.divider()
            tab1, tab2, tab3 = st.tabs(["📅 Next Period", "🌟 Fertility Window", "📊 Cycle Trends"])
            
            with tab1:
                st.success(f"### {(pred_start - timedelta(days=round(variation))).strftime('%d %b')} – {(pred_start + timedelta(days=round(variation))).strftime('%d %b %Y')}")
                st.caption("Predicted start window based on your history.")

            with tab2:
                st.info(f"### {fertile_start.strftime('%d %b')} – {fertile_end.strftime('%d %b')}")
                st.write(f"Estimated Ovulation: **{ovulation_day.strftime('%d %b')}**")

            with tab3:
                # Prepare data for Plotly
                chart_data = pd.DataFrame({
                    "Period Date": all_dates[1:],
                    "Cycle Length": cycle_gaps
                })
                fig = px.line(chart_data, x="Period Date", y="Cycle Length", 
                             title="Cycle Length History", markers=True)
                fig.add_hline(y=avg_cycle, line_dash="dot", annotation_text="Average")
                fig.update_layout(yaxis_title="Days", xaxis_title="Date Logged")
                st.plotly_chart(fig, use_container_width=True)

    else:
        st.info(f"Log at least 2 periods to see trends! (Logged: {len(all_dates)})")
else:
    st.warning("No data found. Log your first period below.")

# 4. Logging Section
st.divider()
st.subheader("Log Actual Start Date")
new_date = st.date_input("Start Date", value=datetime.now())

if st.button("Log Date & Sync Sheet", use_container_width=True):
    if not df.empty and (pd.to_datetime(new_date) - df['Date'].max()).days < 10:
        st.error("Error: You logged a period very recently!")
    else:
        new_entry = pd.DataFrame([{"Date": new_date.strftime("%d/%m/%Y")}])
        updated_df = pd.concat([df[['Date']], new_entry], ignore_index=True)
        updated_df['Date'] = pd.to_datetime(updated_df['Date']).dt.strftime("%d/%m/%Y")
        conn.update(data=updated_df)
        st.cache_data.clear()
        st.rerun()

# 5. History & Data Management
with st.expander("History & Data Management"):
    if not df.empty:
        history_df = df.sort_values(by='Date', ascending=False).copy()
        history_df['Date Display'] = history_df['Date'].dt.strftime('%d %b %Y')
        st.table(history_df[['Date Display']])
        
        if st.button("🗑️ Delete Last Entry"):
            updated_df = df.sort_values(by='Date').iloc[:-1]
            updated_df['Date'] = updated_df['Date'].dt.strftime("%d/%m/%Y")
            conn.update(data=updated_df)
            st.cache_data.clear()
            st.rerun()
