import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import uuid

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Baby Period Tracker",
    page_icon="🩸",
    layout="wide"
)

# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

div[data-testid="stMetric"] {
    background-color: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,0.2);
    padding: 1.2rem;
    border-radius: 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}

.status-card {
    padding: 2rem;
    border-radius: 16px;
    background-color: var(--secondary-background-color);
    border-left: 8px solid;
    margin-bottom: 2rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.status-badge {
    display: inline-block;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    background-color: rgba(128,128,128,0.15);
    margin-right: 0.5rem;
    margin-top: 0.3rem;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# GOOGLE SHEETS CONNECTION
# =========================================================

conn = st.connection("gsheets", type=GSheetsConnection)

# =========================================================
# CACHE DATA
# =========================================================

@st.cache_data(ttl=10)
def get_data():
    try:
        df = conn.read(ttl=0)

        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]

            if 'Date' not in df.columns:
                return pd.DataFrame(columns=['ID', 'Date'])

            df['Date'] = pd.to_datetime(
                df['Date'],
                dayfirst=True,
                format='%d/%m/%Y',
                errors='coerce'
            )

            df = df.dropna(subset=['Date'])
            df = df.sort_values(by='Date')
            return df

    except Exception as e:
        st.error(f"Database connection error: {e}")

    return pd.DataFrame(columns=['ID', 'Date'])

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def remove_outliers(gaps):
    if len(gaps) < 4:
        return gaps

    q1 = np.percentile(gaps, 25)
    q3 = np.percentile(gaps, 75)
    iqr = q3 - q1

    filtered = [
        g for g in gaps
        if (q1 - 1.5 * iqr) <= g <= (q3 + 1.5 * iqr)
    ]

    return filtered if filtered else gaps

def calculate_fertility_probability(days_to_ov):
    score = np.exp(-((days_to_ov) ** 2) / (2 * 2.5 ** 2))
    return round(score * 100)

# =========================================================
# LOAD DATA
# =========================================================

df = get_data()
today = datetime.now().date()

# =========================================================
# TITLE
# =========================================================

st.title("🩸 Baby Period Tracker")
st.caption("Advanced Menstrual Health & Fertility Analytics Dashboard")

# =========================================================
# MAIN ANALYTICS
# =========================================================

if len(df) >= 3:
    all_dates = df['Date'].tolist()
    gaps = [(all_dates[i] - all_dates[i - 1]).days for i in range(1, len(all_dates))]

    # Remove outliers
    gaps = remove_outliers(gaps)

    # Exponential Moving Average
    avg_cycle = pd.Series(gaps).ewm(span=5).mean().iloc[-1]
    std_dev = np.std(gaps)
    last_start = all_dates[-1].date()
    days_since = (today - last_start).days

    # Prediction confidence
    confidence = max(0, 100 - (std_dev * 8))

    # Next predicted cycle
    pred_start_avg = last_start + timedelta(days=round(avg_cycle))
    pred_start_min = pred_start_avg - timedelta(days=round(std_dev))
    pred_start_max = pred_start_avg + timedelta(days=round(std_dev))

    # Adaptive luteal phase
    estimated_luteal = round(np.clip(std_dev + 12, 11, 16))
    ovulation_est = pred_start_avg - timedelta(days=estimated_luteal)
    fertile_start = ovulation_est - timedelta(days=5)
    fertile_end = ovulation_est + timedelta(days=1)
    days_to_ov = (ovulation_est - today).days
    fertility_percent = calculate_fertility_probability(days_to_ov)

    # =====================================================
    # PHASE DETECTION
    # =====================================================
    if days_since < 5:
        phase = "Menstrual Phase"
        color = "#FF4B4B"
        msg = "Rest and recovery phase."
    elif days_since < (ovulation_est - last_start).days:
        phase = "Follicular Phase"
        color = "#00CC96"
        msg = "Estrogen levels increasing."
    elif fertile_start <= today <= fertile_end:
        phase = "Ovulatory Phase"
        color = "#636EFA"
        msg = "Peak fertility window."
    else:
        phase = "Luteal Phase"
        color = "#FFA15A"
        msg = "Progesterone dominant phase."

    # Fertility labels
    if fertility_percent >= 80:
        fertility_label = "Peak 🌟"
    elif fertility_percent >= 50:
        fertility_label = "High 📈"
    elif fertility_percent >= 25:
        fertility_label = "Moderate"
    else:
        fertility_label = "Low 📉"

    # =====================================================
    # HEALTH FLAGS
    # =====================================================
    alerts = []
    if avg_cycle < 21: alerts.append("⚠️ Short cycle length detected.")
    if avg_cycle > 35: alerts.append("⚠️ Long cycle length detected.")
    if std_dev > 7: alerts.append("⚠️ High cycle variability detected.")
    if days_since > 45: alerts.append("⚠️ Possible missed cycle detected.")

    # =====================================================
    # STATUS CARD
    # =====================================================
    st.markdown(f"""
    <div class="status-card" style="border-left-color:{color};">
        <h4 style="margin-top:0;opacity:0.7;">CURRENT BIOLOGICAL STATUS</h4>
        <h1 style="color:{color};margin-bottom:1rem;">{phase}</h1>
        <span class="status-badge">Day {days_since + 1}</span>
        <span class="status-badge">Fertility: {fertility_label}</span>
        <span class="status-badge">Confidence: {round(confidence)}%</span>
        <span class="status-badge">±{round(std_dev,1)}d Variance</span>
        <p style="margin-top:1rem;">{msg}</p>
    </div>
    """, unsafe_allow_html=True)

    # =====================================================
    # ALERTS
    # =====================================================
    for a in alerts:
        st.warning(a)

    # =====================================================
    # METRICS
    # =====================================================
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Next Period", pred_start_avg.strftime("%b %d"), f"{(pred_start_avg - today).days} days")
    with m2: st.metric("Ovulation", ovulation_est.strftime("%b %d"), fertility_label)
    with m3: st.metric("Average Cycle", f"{round(avg_cycle)} Days")
    with m4: st.metric("Fertility Probability", f"{fertility_percent}%")

    st.write("---")

    # =====================================================
    # TABS
    # =====================================================
    tab1, tab2, tab3 = st.tabs(["🔄 Cycle Overview", "📊 Historical Trends", "✍️ Log Data"])

    # =====================================================
    # TAB 1: OVERVIEW
    # =====================================================
    with tab1:
        col1, col2 = st.columns([1.5, 1])
        with col1:
            mens_days = 5
            follicular_days = max((ovulation_est - last_start).days - mens_days, 1)
            fertile_days = 6
            luteal_days = max(round(avg_cycle) - (mens_days + follicular_days + fertile_days), 1)

            fig = go.Figure(data=[go.Pie(
                labels=['Menstrual', 'Follicular', 'Fertile', 'Luteal'],
                values=[mens_days, follicular_days, fertile_days, luteal_days],
                hole=0.7, textinfo='none', hoverinfo='label+value',
                marker_colors=['#FF4B4B', '#00CC96', '#636EFA', '#FFA15A']
            )])
            fig.update_layout(height=350, margin=dict(t=30, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.write("### 📅 Upcoming Milestones")
            st.info(f"**Fertile Window Begins**\n\n{fertile_start.strftime('%A, %B %d')}")
            st.success(f"**Estimated Ovulation**\n\n{ovulation_est.strftime('%A, %B %d')}")
            st.error(f"**Predicted Period Window**\n\n{pred_start_min.strftime('%b %d')} → {pred_start_max.strftime('%b %d')}")

    # =====================================================
    # TAB 2: TRENDS
    # =====================================================
    with tab2:
        st.write("### Cycle Length Analysis")
        colors = ["#00CC96" if (avg_cycle - std_dev) <= g <= (avg_cycle + std_dev) else "#FF4B4B" for g in gaps]

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=[f"Cycle {i+1}" for i in range(len(gaps))], y=gaps, marker_color=colors, text=gaps, textposition='auto'))
        fig2.add_hline(y=avg_cycle, line_dash="dash", line_color="#888", annotation_text="Average")
        fig2.update_layout(height=350, yaxis_title="Days", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

        trend_df = pd.DataFrame({"Date": all_dates[1:], "Cycle Length": gaps})
        fig3 = px.line(trend_df, x="Date", y="Cycle Length", markers=True)
        fig3.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)

    # =====================================================
    # TAB 3: LOGGING
    # =====================================================
    with tab3:
        col_form, col_manage = st.columns([2, 1])
        with col_form:
            with st.form("log_form", clear_on_submit=True):
                st.write("### Log New Cycle Start")
                log_date = st.date_input("Start Date", today)
                submitted = st.form_submit_button("Save to Google Sheets", use_container_width=True)

                if submitted:
                    formatted_date = log_date.strftime("%d/%m/%Y")
                    # Safe string comparison for duplicates
                    if log_date > today:
                        st.error("Future dates are not allowed.")
                    elif formatted_date in df['Date'].dt.strftime("%d/%m/%Y").values:
                        st.warning("This date already exists.")
                    else:
                        new_row = pd.DataFrame([{"ID": str(uuid.uuid4()), "Date": formatted_date}])
                        existing = df.copy()
                        if 'ID' not in existing.columns:
                            existing['ID'] = [str(uuid.uuid4()) for _ in range(len(existing))]
                        existing['Date'] = existing['Date'].dt.strftime("%d/%m/%Y")
                        
                        updated_df = pd.concat([existing, new_row], ignore_index=True)
                        conn.update(data=updated_df)
                        st.cache_data.clear()
                        st.success("Cycle logged successfully.")
                        st.rerun()

        with col_manage:
            st.write("### Data Management")
            if st.button("🗑️ Undo Last Log", use_container_width=True):
                if not df.empty:
                    updated_df = df.iloc[:-1].copy()
                    updated_df['Date'] = updated_df['Date'].dt.strftime("%d/%m/%Y")
                    conn.update(data=updated_df)
                    st.cache_data.clear()
                    st.success("Last log removed.")
                    st.rerun()

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV", data=csv, file_name="period_tracker_data.csv", mime="text/csv", use_container_width=True)

            with st.expander("View Raw Data"):
                st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True, hide_index=True)

# =========================================================
# FIRST TIME USER
# =========================================================
else:
    st.info(f"👋 Welcome! You have {len(df)} entry/entries. Please log at least 3 previous cycle start dates to activate predictions.")
    
    with st.form("initial_log"):
        d = st.date_input("Period Start Date", today)
        submit = st.form_submit_button("Log Initial Date")

        if submit:
            formatted_date = d.strftime("%d/%m/%Y")
            if d > today:
                st.error("Future dates are not allowed.")
            # Safe string comparison for duplicates
            elif not df.empty and formatted_date in df['Date'].dt.strftime("%d/%m/%Y").values:
                st.warning("This date already exists.")
            else:
                new_row = pd.DataFrame([{"ID": str(uuid.uuid4()), "Date": formatted_date}])
                
                # Critical Fix: Concatenate with existing data instead of overwriting
                if not df.empty:
                    existing = df.copy()
                    if 'ID' not in existing.columns:
                        existing['ID'] = [str(uuid.uuid4()) for _ in range(len(existing))]
                    existing['Date'] = existing['Date'].dt.strftime("%d/%m/%Y")
                    updated_df = pd.concat([existing, new_row], ignore_index=True)
                else:
                    updated_df = new_row

                conn.update(data=updated_df)
                st.cache_data.clear()
                st.success("Date logged.")
                st.rerun()
