import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import statistics

st.set_page_config(page_title="Baby Period Tracker🩸", page_icon="🩸")

st.title("🩸 Baby Period Tracker")

# Connect to the Sheet using the URL you provided
# We use 'gsheets' connection which looks for secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# Read existing data
df = conn.read(ttl=0) # ttl=0 ensures it doesn't cache old data

if not df.empty:
    # Convert your DD-MM-YYYY format to datetime
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    dates = sorted(df['Date'].tolist())

    if len(dates) >= 2:
        # Calculate Cycle Math
        cycle_lengths = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        avg_cycle = statistics.mean(cycle_lengths)
        std_dev = statistics.stdev(cycle_lengths) if len(cycle_lengths) > 1 else 2
        
        last_start = dates[-1]
        next_start = last_start + timedelta(days=round(avg_cycle - std_dev))
        next_end = last_start + timedelta(days=round(avg_cycle + std_dev))

        # Metrics display
        col1, col2 = st.columns(2)
        col1.metric("Avg Cycle", f"{round(avg_cycle, 1)} days")
        col2.metric("Last Period", last_start.strftime('%d-%m-%Y'))

        st.success(f"### 🎯 Predicted: **{next_start.strftime('%d %b')}** — **{next_end.strftime('%d %b %Y')}**")

# Input for new dates
st.divider()
st.subheader("Add New Entry")
new_date_input = st.date_input("When did it start?", value=datetime.now())

if st.button("Save to Google Sheets"):
    new_date_str = new_date_input.strftime("%d-%m-%Y")
    
    # Create new row
    new_row = pd.DataFrame([{"Date": new_date_str}])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    
    # Write back to Sheet
    conn.update(data=updated_df)
    st.cache_data.clear()
    st.success("Successfully updated!")
    st.rerun()

st.subheader("History Log")
st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)
