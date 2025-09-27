import streamlit as st
import sqlite3
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go

# ------------------ Database Setup ------------------ #
conn = sqlite3.connect("sales_pipeline.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    stage TEXT,
    deal_value REAL,
    follow_up_date TEXT,
    created_at TEXT
)
''')
conn.commit()

# ------------------ Helper Functions ------------------ #
def add_lead(name, email, stage, deal_value, follow_up_date):
    c.execute("INSERT INTO leads (name, email, stage, deal_value, follow_up_date, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (name, email, stage, deal_value, follow_up_date, datetime.datetime.now().strftime("%Y-%m-%d")))
    conn.commit()

def fetch_leads():
    return pd.read_sql("SELECT * FROM leads", conn)

def update_lead(lead_id, stage, follow_up_date):
    c.execute("UPDATE leads SET stage=?, follow_up_date=? WHERE id=?",
              (stage, follow_up_date, lead_id))
    conn.commit()

def delete_lead(lead_id):
    c.execute("DELETE FROM leads WHERE id=?", (lead_id,))
    conn.commit()

# ------------------ Streamlit UI ------------------ #
st.set_page_config(page_title="Sales Pipeline Automation", layout="wide")
st.title("📈 Sales Pipeline Automation System")

tab1, tab2, tab3 = st.tabs(["Leads", "Reminders", "Analytics"])

# ------------------ Phase 1: Lead Management ------------------ #
with tab1:
    st.subheader("➕ Add New Lead")
    with st.form("lead_form"):
        name = st.text_input("Client Name")
        email = st.text_input("Client Email")
        stage = st.selectbox("Sales Stage", ["New", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost"])
        deal_value = st.number_input("Deal Value ($)", min_value=0.0, step=100.0)
        follow_up_date = st.date_input("Follow-up Date", datetime.date.today())
        submitted = st.form_submit_button("Add Lead")

        if submitted and name and email:
            add_lead(name, email, stage, deal_value, follow_up_date.strftime("%Y-%m-%d"))
            st.success(f"✅ Lead added for {name}")

    st.markdown("---")
    st.subheader("📋 Current Leads")
    leads_df = fetch_leads()
    if not leads_df.empty:
        st.dataframe(leads_df)

        # Update or Delete
        lead_id = st.selectbox("Select Lead ID to Update/Delete", leads_df["id"])
        new_stage = st.selectbox("Update Stage", ["New", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost"])
        new_follow_up = st.date_input("New Follow-up Date", datetime.date.today())

        if st.button("Update Lead"):
            update_lead(lead_id, new_stage, new_follow_up.strftime("%Y-%m-%d"))
            st.success("✅ Lead updated!")

        if st.button("Delete Lead"):
            delete_lead(lead_id)
            st.warning("⚠️ Lead deleted!")
    else:
        st.info("No leads yet. Add one above.")

# ------------------ Phase 2: Automated Reminders ------------------ #
with tab2:
    st.subheader("⏰ Follow-up Reminders")
    leads_df = fetch_leads()
    if not leads_df.empty:
        leads_df["follow_up_date"] = pd.to_datetime(leads_df["follow_up_date"], errors="coerce")
        today = pd.to_datetime(datetime.date.today())

        overdue = leads_df[leads_df["follow_up_date"] < today]
        due_today = leads_df[leads_df["follow_up_date"] == today]

        if not overdue.empty:
            st.error("⚠️ Overdue Follow-ups")
            st.table(overdue[["id", "name", "email", "stage", "follow_up_date"]])

        if not due_today.empty:
            st.warning("📌 Due Today")
            st.table(due_today[["id", "name", "email", "stage", "follow_up_date"]])

        if overdue.empty and due_today.empty:
            st.success("🎉 No pending follow-ups today!")
    else:
        st.info("No leads available for reminders.")

# ------------------ Phase 3: Analytics Dashboard ------------------ #
with tab3:
    st.subheader("📊 Sales Analytics Dashboard")
    leads_df = fetch_leads()

    if leads_df.empty:
        st.info("No data for analytics yet.")
    else:
        # ---- KPIs ----
        total_value = leads_df["deal_value"].sum()
        won_value = leads_df[leads_df["stage"] == "Won"]["deal_value"].sum()
        lost_value = leads_df[leads_df["stage"] == "Lost"]["deal_value"].sum()
        avg_deal = leads_df["deal_value"].mean() if not leads_df.empty else 0
        conversion_rate = (won_value / total_value * 100) if total_value > 0 else 0

        leads_df["created_at"] = pd.to_datetime(leads_df["created_at"], errors="coerce")
        leads_df["follow_up_date"] = pd.to_datetime(leads_df["follow_up_date"], errors="coerce")
        won_df = leads_df[leads_df["stage"] == "Won"].copy()
        if not won_df.empty:
            won_df["days_to_close"] = (won_df["follow_up_date"] - won_df["created_at"]).dt.days
            avg_time_close = won_df["days_to_close"].mean()
        else:
            avg_time_close = 0

        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("💰 Total Pipeline", f"${total_value:,.0f}")
        kpi2.metric("🏆 Won Value", f"${won_value:,.0f}")
        kpi3.metric("❌ Lost Value", f"${lost_value:,.0f}")
        kpi4.metric("📈 Conversion Rate", f"{conversion_rate:.1f}%")
        kpi5.metric("⏱ Avg Time-to-Close", f"{avg_time_close:.1f} days")

        st.markdown("---")

        # ---- Funnel Chart ----
        stage_order = ["New", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost"]
        stage_counts = leads_df["stage"].value_counts().reindex(stage_order, fill_value=0)

        funnel_fig = go.Figure(go.Funnel(
            y=stage_counts.index,
            x=stage_counts.values,
            textinfo="value+percent previous"
        ))
        st.plotly_chart(funnel_fig, use_container_width=True)

        # ---- Revenue Trend ----
        leads_df["month"] = leads_df["created_at"].dt.to_period("M").astype(str)
        monthly_value = leads_df.groupby("month")["deal_value"].sum().reset_index()

        revenue_fig = px.line(monthly_value, x="month", y="deal_value", markers=True,
                              title="Monthly Deal Value Added")
        st.plotly_chart(revenue_fig, use_container_width=True)

        # ---- Win/Loss Pie ----
        win_loss_counts = leads_df[leads_df["stage"].isin(["Won", "Lost"])]["stage"].value_counts()
        if not win_loss_counts.empty:
            pie_fig = px.pie(names=win_loss_counts.index, values=win_loss_counts.values,
                             title="Won vs Lost Deals", color=win_loss_counts.index,
                             color_discrete_map={"Won": "green", "Lost": "red"})
            st.plotly_chart(pie_fig, use_container_width=True)
        else:
            st.info("No Won/Lost deals yet for pie chart.")
