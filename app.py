import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import statistics

st.set_page_config(page_title="Baby Period Tracker🩸", page_icon="🩸")

# 1. Setup Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Fetch History (ttl=0 ensures we always get the latest logs)
df = conn.read(ttl=0)

st.title("🩸 Period Predictor & Logger")

if not df.empty:
    # Clean data: Standardize headers and convert dates
    df.columns = [str(c).strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date']).sort_values(by='Date')
    
    all_dates = df['Date'].tolist()

    if len(all_dates) >= 2:
        # Calculate gaps between every period in your history
        cycle_gaps = [(all_dates[i] - all_dates[i-1]).days for i in range(1, len(all_dates))]
        
        # Filter out unrealistic gaps (e.g., typing errors where gap < 15 days)
        valid_gaps = [g for g in cycle_gaps if g > 15]
        
        if valid_gaps:
            avg_cycle = statistics.mean(valid_gaps)
            variation = statistics.stdev(valid_gaps) if len(valid_gaps) > 1 else 2
            
            # Predict based on the MOST RECENT date in the sheet
            last_date = all_dates[-1]
            pred_start = last_date + timedelta(days=round(avg_cycle - variation))
            pred_end = last_start = last_date + timedelta(days=round(avg_cycle + variation))

            # UI Display
            st.subheader("Next Predicted Cycle")
            st.info(f"Based on your history, your next period is expected between:")
            st.header(f"⏳ {pred_start.strftime('%d %b')} – {pred_end.strftime('%d %b %Y')}")
            
            col1, col2 = st.columns(2)
            col1.metric("Average Cycle", f"{round(avg_cycle, 1)} days")
            col2.metric("Last Logged", last_date.strftime('%d %b %Y'))

# 3. Logging Section
st.divider()
st.subheader("Log Actual Start Date")
st.write("When your period starts, select the date below to update the predictor:")

new_date = st.date_input("Start Date", value=datetime.now())

if st.button("Log Date & Update Sheet"):
    # Prepare the data to be saved
    new_entry = pd.DataFrame([{"Date": new_date.strftime("%d/%m/%Y")}])
    
    # Combine old data with the new entry
    # We use a simple DataFrame format to ensure it matches your sheet's column 'Date'
    updated_df = pd.concat([df[['Date']], new_entry], ignore_index=True)
    
    # Convert back to string format for Google Sheets storage
    updated_df['Date'] = pd.to_datetime(updated_df['Date']).dt.strftime("%d/%m/%Y")
    
    # Write to Google Sheets
    conn.update(data=updated_df)
    
    # Reset app to show new prediction
    st.cache_data.clear()
    st.success(f"Logged {new_date.strftime('%d %b %Y')}! Recalculating...")
    st.rerun()

# 4. History View (Collapsible)
with st.expander("View Full History"):
    st.table(df.sort_values(by='Date', ascending=False)['Date'].dt.strftime('%d-%m-%Y'))
