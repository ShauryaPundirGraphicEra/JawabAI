import traceback
from langsmith import Client
import streamlit as st
import sqlite3
import pandas as pd
import uuid
from agent import workflow # Ensure your compiled LangGraph is in agent.py
import time 

if "has_run" not in st.session_state:
    st.session_state["has_run"] = False

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = None

st.set_page_config(page_title="ITSM Command Center", page_icon="📊", layout="wide")

# --- 1. Database Connection ---
def load_data():
    try:
        conn = sqlite3.connect('itsm_portal.db')
        df = pd.read_sql_query("SELECT * FROM tickets ORDER BY timestamp DESC", conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame() # Return empty if DB doesn't exist yet

df = load_data()

# --- 2. Sidebar: Email Ingestion Simulator ---
with st.sidebar:
    st.header("📧 Simulate Incoming Email")
    st.markdown("Trigger the LangGraph workflow as if an email just hit the service desk inbox.")
    
    with st.form("email_intake_form"):
        subject = st.text_input("Subject Line")
        body = st.text_area("Email Body")
        submit_email = st.form_submit_button("Process Email via AI Agent")
        
        if submit_email and subject and body:
            with st.spinner("Agentic Workflow Running..."):
                # Construct the config and state
                ticket_uuid = f"TKT-EMAIL-{str(uuid.uuid4())[:6].upper()}"
                input_state = {
                    "ticket_id": ticket_uuid,
                    "original_title": subject,
                    "original_description": body
                }
                config = {"configurable": {"thread_id": ticket_uuid}}
                
                st.session_state["thread_id"] = ticket_uuid
                st.session_state["has_run"] = True
                workflow.invoke(input_state, config)
            st.success("Email processed and logged to DB!")
            
                
                
            st.rerun() # Refresh the dashboard to show the new ticket
    if st.session_state.get("has_run"):

        if st.button("▶️ Resume Previous Workflow"):
            thread_id = st.session_state.get("thread_id")

            if thread_id:
                config = {"configurable": {"thread_id": thread_id}}

                try:
                    workflow.invoke(None, config)
                    st.success("Workflow resumed successfully!")
                except Exception:
                    st.error(traceback.format_exc())
            else:
                st.error("No previous workflow found.")

# --- 3. Main Dashboard ---
st.title("📊 ITSM Command Center")
st.write("SESSION STATE:", st.session_state)

if df.empty:
    st.info("The database is currently empty. Use the sidebar to simulate an incoming email.")
else:
    # --- A. Top Level Metrics ---
    st.markdown("### Live Operations Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    total_tickets = len(df)
    auto_resolved = len(df[df['final_status'] == 'RESOLVED_AUTO'])
    escalated = len(df[df['final_status'].str.contains('ESCALATED', na=False)])
    
    # Calculate Automation Rate safely
    automation_rate = round((auto_resolved / total_tickets) * 100, 1) if total_tickets > 0 else 0.0

    col1.metric("Total Tickets", total_tickets)
    col2.metric("Auto-Resolved (RAG)", auto_resolved)
    col3.metric("Escalated to Human", escalated)
    col4.metric("AI Automation Rate", f"{automation_rate}%")

    st.divider()

    # --- B. Visualizations ---
    colA, colB = st.columns(2)
    
    with colA:
        st.markdown("**Tickets by Queue**")
        queue_counts = df['queue'].value_counts()
        st.bar_chart(queue_counts)
        
    with colB:
        st.markdown("**Tickets by ITIL Type**")
        type_counts = df['ticket_type'].value_counts()
        st.bar_chart(type_counts)

    st.divider()

    # --- C. The Escalation Queue (Actionable Data) ---
    st.markdown("### 🚨 Escalation Queue (Requires Human Action)")
    
    # Filter for tickets that the AI couldn't resolve
    df_escalated = df[df['final_status'].str.contains('ESCALATED', na=False)]
    
    if not df_escalated.empty:
        # Display as a clean, interactive dataframe
        st.dataframe(
            df_escalated[['ticket_id', 'timestamp', 'queue', 'priority', 'ticket_type', 'final_status']],
            use_container_width=True,
            hide_index=True
        )
        
        # Let the human agent inspect a specific ticket
        st.markdown("**Inspect Escalated Ticket Details**")
        selected_ticket = st.selectbox("Select a Ticket ID to review:", df_escalated['ticket_id'])
        
        if selected_ticket:
            ticket_data = df_escalated[df_escalated['ticket_id'] == selected_ticket].iloc[0]
            st.info(f"**Original Email:** {ticket_data['original_description']}")
            st.warning(f"**AI Proposed Resolution (Failed/Escalated):** {ticket_data['proposed_resolution']}")
    else:
        st.success("Zero escalations! The AI is handling 100% of the current queue.")

    st.divider()

    # --- D. All Tickets (Audit Log) ---
    st.markdown("### 🗄️ All Tickets (Audit Log)")
    st.markdown("A complete master record of all tickets processed by the AI system.")

    # Display the full dataframe
    st.dataframe(
        df[['ticket_id', 'timestamp', 'queue', 'priority', 'ticket_type', 'final_status']],
        use_container_width=True,
        hide_index=True
    )

    # Let the human agent inspect ANY ticket
    st.markdown("**Inspect Any Ticket Record**")
    # We use a unique key="audit_select" so Streamlit doesn't confuse this dropdown with the escalation one
    selected_audit_ticket = st.selectbox("Select a Ticket ID from the master log:", df['ticket_id'], key="audit_select")
    
    if selected_audit_ticket:
        audit_ticket_data = df[df['ticket_id'] == selected_audit_ticket].iloc[0]
        st.info(f"**Original Email:** {audit_ticket_data['original_description']}")
        
        # Color code the resolution box based on whether the AI succeeded or failed
        if audit_ticket_data['final_status'] == 'RESOLVED_AUTO':
            st.success(f"**AI Proposed Resolution (Sent to User):**\n\n{audit_ticket_data['proposed_resolution']}")
        else:
            st.error(f"**AI Proposed Resolution (Blocked by Guardrails):**\n\n{audit_ticket_data['proposed_resolution']}")



# import streamlit as st
# import sqlite3
# import pandas as pd
# import uuid
# from agent import workflow # Ensure your compiled LangGraph is in agent.py

# st.set_page_config(page_title="ITSM Command Center", page_icon="📊", layout="wide")

# # --- 1. Database Connection ---
# def load_data():
#     try:
#         conn = sqlite3.connect('itsm_portal.db')
#         df = pd.read_sql_query("SELECT * FROM tickets ORDER BY timestamp DESC", conn)
#         conn.close()
#         return df
#     except Exception as e:
#         return pd.DataFrame() # Return empty if DB doesn't exist yet

# df = load_data()

# # --- 2. Sidebar: Email Ingestion Simulator ---
# with st.sidebar:
#     st.header("📧 Simulate Incoming Email")
#     st.markdown("Trigger the LangGraph workflow as if an email just hit the service desk inbox.")
    
#     with st.form("email_intake_form"):
#         subject = st.text_input("Subject Line")
#         body = st.text_area("Email Body")
#         submit_email = st.form_submit_button("Process Email via AI Agent")
        
#         if submit_email and subject and body:
#             with st.spinner("Agentic Workflow Running..."):
#                 # Construct the state just like an email parser would
#                 ticket_uuid = f"TKT-EMAIL-{str(uuid.uuid4())[:6].upper()}"
#                 input_state = {
#                     "ticket_id": ticket_uuid,
#                     "original_title": subject,
#                     "original_description": body
#                 }
#                 config = {"configurable": {"thread_id": ticket_uuid}}
                
                
#                 workflow.invoke(input_state, config)
#             st.success("Email processed and logged to DB!")
#             st.rerun() # Refresh the dashboard to show the new ticket

# # --- 3. Main Dashboard ---
# st.title("📊 ITSM Command Center")

# if df.empty:
#     st.info("The database is currently empty. Use the sidebar to simulate an incoming email.")
# else:
#     # --- A. Top Level Metrics ---
#     st.markdown("### Live Operations Metrics")
#     col1, col2, col3, col4 = st.columns(4)
    
#     total_tickets = len(df)
#     auto_resolved = len(df[df['final_status'] == 'RESOLVED_AUTO'])
#     escalated = len(df[df['final_status'].str.contains('ESCALATED', na=False)])
    
#     # Calculate Automation Rate safely
#     automation_rate = round((auto_resolved / total_tickets) * 100, 1) if total_tickets > 0 else 0.0

#     col1.metric("Total Tickets", total_tickets)
#     col2.metric("Auto-Resolved (RAG)", auto_resolved)
#     col3.metric("Escalated to Human", escalated)
#     col4.metric("AI Automation Rate", f"{automation_rate}%")

#     st.divider()

#     # --- B. Visualizations ---
#     colA, colB = st.columns(2)
    
#     with colA:
#         st.markdown("**Tickets by Queue**")
#         queue_counts = df['queue'].value_counts()
#         st.bar_chart(queue_counts)
        
#     with colB:
#         st.markdown("**Tickets by ITIL Type**")
#         type_counts = df['ticket_type'].value_counts()
#         st.bar_chart(type_counts)

#     st.divider()

#     # --- C. The Helpdesk Queue (Actionable Data) ---
#     st.markdown("### Escalation Queue (Requires Human Action)")
    
#     # Filter for tickets that the AI couldn't resolve
#     df_escalated = df[df['final_status'].str.contains('ESCALATED', na=False)]
    
#     if not df_escalated.empty:
#         # Display as a clean, interactive dataframe
#         st.dataframe(
#             df_escalated[['ticket_id', 'timestamp', 'queue', 'priority', 'ticket_type', 'final_status']],
#             use_container_width=True,
#             hide_index=True
#         )
        
#         # Let the human agent inspect a specific ticket
#         st.markdown("**Inspect Ticket Details**")
#         selected_ticket = st.selectbox("Select a Ticket ID to review:", df_escalated['ticket_id'])
        
#         if selected_ticket:
#             ticket_data = df_escalated[df_escalated['ticket_id'] == selected_ticket].iloc[0]
#             st.info(f"**Original Email:** {ticket_data['original_description']}")
#             st.warning(f"**AI Proposed Resolution (Failed/Escalated):** {ticket_data['proposed_resolution']}")
#     else:
#         st.success("Zero escalations! The AI is handling 100% of the current queue.")