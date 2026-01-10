import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# 1. Page Configuration
st.set_page_config(page_title="Baby Period Tracker🩸", page_icon="🩸", layout="centered")

# 2. Setup Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Fetch and Clean Data
df = conn.read(ttl=0)

st.title("🩸 Period Predictor & Logger")

# Ensure DataFrame is usable
if not df.empty:
    df.columns = [str(c).strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date']).sort_values(by='Date')
    all_dates = df['Date'].tolist()

    if len(all_dates) >= 2:
        # Calculate days between each period
        cycle_gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
        
        # --- ACCURACY LOGIC ---
        series_gaps = pd.Series(cycle_gaps)
        
        # Remove Outliers (IQR Method)
        q1 = series_gaps.quantile(0.25)
        q3 = series_gaps.quantile(0.75)
        iqr = q3 - q1
        valid_gaps = series_gaps[(series_gaps >= q1 - 1.5 * iqr) & (series_gaps <= q3 + 1.5 * iqr)].tolist()
        
        # Fallback if filtering leaves too few data points
        if len(valid_gaps) < 2:
            valid_gaps = [g for g in cycle_gaps if 15 < g < 50]

        if valid_gaps:
            # Weighted Average (Recent cycles are 2x as important)
            weights = np.ones(len(valid_gaps))
            if len(weights) >= 3:
                weights[-3:] = 2.0 
            
            avg_cycle = np.average(valid_gaps, weights=weights)
            std_dev = np.std(valid_gaps) if len(valid_gaps) > 1 else 2
            
            # Prediction Window Calculation
            # Formula: Last Logged Date + (Average Cycle ± Standard Deviation)
            variation = min(std_dev, 4) # Caps the window range for better UI
            last_date = all_dates[-1]
            
            pred_start = last_date + timedelta(days=round(avg_cycle - variation))
            pred_end = last_date + timedelta(days=round(avg_cycle + variation))

            # --- UI DISPLAY ---
            st.subheader("Next Predicted Cycle")
            reliability = "High" if std_dev < 3 else "Moderate" if std_dev < 5 else "Variable"
            st.markdown(f"Status: **{reliability} Reliability**")
            
            st.success(f"### ⏳ {pred_start.strftime('%d %b')} – {pred_end.strftime('%d %b %Y')}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Avg Cycle", f"{round(avg_cycle, 1)} days")
            col2.metric("Last Logged", last_date.strftime('%d %b'))
            col3.metric("Variation", f"±{round(variation, 1)} days")
    else:
        st.info("Log at least 2 periods to see predictions!")
else:
    st.warning("No data found in the Google Sheet. Please check your connection or log a date.")

# 4. Logging Section
st.divider()
st.subheader("Log Actual Start Date")
st.write("Enter the date your period started to update the model:")

new_date = st.date_input("Start Date", value=datetime.now())

if st.button("Log Date & Sync Sheet"):
    # Prepare new entry
    new_entry = pd.DataFrame([{"Date": new_date.strftime("%d/%m/%Y")}])
    
    # Combine and format
    # We keep only the 'Date' column to match the sheet
    updated_df = pd.concat([df[['Date']], new_entry], ignore_index=True)
    updated_df['Date'] = pd.to_datetime(updated_df['Date']).dt.strftime("%d/%m/%Y")
    
    # Update Google Sheets
    conn.update(data=updated_df)
    
    # Clear cache and refresh
    st.cache_data.clear()
    st.toast(f"Successfully logged {new_date.strftime('%d %b')}!")
    st.rerun()

# 5. History View
with st.expander("View Full History"):
    if not df.empty:
        history_df = df.sort_values(by='Date', ascending=False).copy()
        history_df['Date'] = history_df['Date'].dt.strftime('%d %b %Y')
        st.table(history_df['Date'])
