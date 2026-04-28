import traceback
from langsmith import Client
import streamlit as st
import sqlite3
import pandas as pd
import uuid
import os
from agent import workflow # Ensure your compiled LangGraph is in agent.py
import time 

# Initialize session state for fault tolerance
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
                
                try:
                    workflow.invoke(input_state, config)
                    st.success("Email processed and logged to DB!")
                except Exception as e:
                    st.error(f"Workflow paused due to error: {e}")
                    
            st.rerun() # Refresh the dashboard to show the new ticket

    # Fault Tolerance: Resume Workflow Button
    if st.session_state.get("has_run"):
        if st.button("▶️ Resume Previous Workflow"):
            thread_id = st.session_state.get("thread_id")
            if thread_id:
                config = {"configurable": {"thread_id": thread_id}}
                with st.spinner("Resuming workflow from last checkpoint..."):
                    try:
                        workflow.invoke(None, config)
                        st.success("Workflow resumed and completed successfully!")
                        st.rerun()
                    except Exception:
                        st.error(traceback.format_exc())
            else:
                st.error("No previous workflow found.")

# --- 3. Main Dashboard ---
st.title("📊 ITSM Command Center & AI Observability")

if df.empty:
    st.info("The database is currently empty. Use the sidebar to simulate an incoming email.")
else:
    # Create enterprise tabs for different views
    tab1, tab2, tab3 = st.tabs(["🚨 Helpdesk Queue", "🗄️ Audit Log", "📈 AI Observability"])

    # ==========================================
    # TAB 1: HELPDESK QUEUE & METRICS
    # ==========================================
    with tab1:
        st.markdown("### Live Operations Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        total_tickets = len(df)
        auto_resolved = len(df[df['final_status'] == 'RESOLVED_AUTO'])
        escalated = len(df[df['final_status'].str.contains('ESCALATED', na=False)])
        
        automation_rate = round((auto_resolved / total_tickets) * 100, 1) if total_tickets > 0 else 0.0

        col1.metric("Total Tickets", total_tickets)
        col2.metric("Auto-Resolved (RAG)", auto_resolved)
        col3.metric("Escalated to Human", escalated)
        col4.metric("AI Automation Rate", f"{automation_rate}%")

        st.divider()

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

        st.markdown("### 🚨 Escalation Queue (Requires Human Action)")
        df_escalated = df[df['final_status'].str.contains('ESCALATED', na=False)]
        
        if not df_escalated.empty:
            st.dataframe(
                df_escalated[['ticket_id', 'timestamp', 'queue', 'priority', 'ticket_type', 'final_status']],
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("**Inspect Escalated Ticket Details**")
            selected_ticket = st.selectbox("Select a Ticket ID to review:", df_escalated['ticket_id'])
            
            if selected_ticket:
                ticket_data = df_escalated[df_escalated['ticket_id'] == selected_ticket].iloc[0]
                st.info(f"**Original Email:** {ticket_data['original_description']}")
                st.warning(f"**AI Proposed Resolution (Failed/Escalated):** {ticket_data['proposed_resolution']}")
        else:
            st.success("Zero escalations! The AI is handling 100% of the current queue.")

    # ==========================================
    # TAB 2: MASTER AUDIT LOG
    # ==========================================
    with tab2:
        st.markdown("### 🗄️ All Tickets (Audit Log)")
        st.markdown("A complete master record of all tickets processed by the AI system.")

        st.dataframe(
            df[['ticket_id', 'timestamp', 'queue', 'priority', 'ticket_type', 'final_status']],
            use_container_width=True,
            hide_index=True
        )

        st.markdown("**Inspect Any Ticket Record**")
        selected_audit_ticket = st.selectbox("Select a Ticket ID from the master log:", df['ticket_id'], key="audit_select")
        
        if selected_audit_ticket:
            audit_ticket_data = df[df['ticket_id'] == selected_audit_ticket].iloc[0]
            st.info(f"**Original Email:** {audit_ticket_data['original_description']}")
            
            if audit_ticket_data['final_status'] == 'RESOLVED_AUTO':
                st.success(f"**AI Proposed Resolution (Sent to User):**\n\n{audit_ticket_data['proposed_resolution']}")
            else:
                st.error(f"**AI Proposed Resolution (Blocked by Guardrails):**\n\n{audit_ticket_data['proposed_resolution']}")

    # ==========================================
    # TAB 3: AI OBSERVABILITY (LANGSMITH & RAGAS)
    # ==========================================
    with tab3:
        st.header("📈 AI Agent Telemetry & Accuracy")
        
        col_ragas, col_smith = st.columns(2)
        
        with col_ragas:
            st.subheader("1. RAGAS Quality Metrics")
            st.markdown("Mathematical evaluation of the RAG pipeline's accuracy and hallucination rate.")
            try:
                ragas_df = pd.read_csv("ragas_evaluation_report.csv")
                
                avg_faithfulness = ragas_df['faithfulness'].mean() * 100
                avg_relevancy = ragas_df['answer_relevancy'].mean() * 100
                avg_precision = ragas_df['context_precision'].mean() * 100
                
                r_col1, r_col2, r_col3 = st.columns(3)
                r_col1.metric("Faithfulness", f"{avg_faithfulness:.1f}%")
                r_col2.metric("Answer Relevancy", f"{avg_relevancy:.1f}%")
                r_col3.metric("Context Precision", f"{avg_precision:.1f}%")
                
                st.dataframe(ragas_df[['question', 'faithfulness', 'answer_relevancy']], hide_index=True)
            except FileNotFoundError:
                st.warning("RAGAS report not found. Run the `eval_ragas.py` script to generate accuracy metrics.")

        with col_smith:
            st.subheader("2. LangSmith Trace Analytics")
            st.markdown("Live execution latency and API token tracking pulled from LangSmith.")
            
            try:
                ls_client = Client()
                # Ensure this matches the LANGCHAIN_PROJECT in your .env file
                project_name = os.getenv("LANGCHAIN_PROJECT", "ITSM_Agent_Production")
                
                # Fetch the last 15 root-level runs
                runs = list(ls_client.list_runs(
                    project_name=project_name, 
                    execution_order=1, 
                    limit=15
                ))
                
                if runs:
                    graph_data = []
                    for r in runs:
                        if r.end_time and r.start_time:
                            latency = (r.end_time - r.start_time).total_seconds()
                            tokens = r.total_tokens if r.total_tokens else 0
                            graph_data.append({"Run ID": str(r.id)[:8], "Latency (s)": latency, "Total Tokens": tokens})
                    
                    ls_df = pd.DataFrame(graph_data)
                    
                    if not ls_df.empty:
                        st.markdown("**Graph Execution Latency (seconds)**")
                        st.line_chart(ls_df.set_index("Run ID")["Latency (s)"])
                        
                        st.markdown("**Token Consumption per Ticket**")
                        st.bar_chart(ls_df.set_index("Run ID")["Total Tokens"])
                else:
                    st.info(f"No LangSmith runs found for project '{project_name}'. Process a ticket to see telemetry.")
                    
            except Exception as e:
                st.error("Could not connect to LangSmith API. Ensure LANGCHAIN_API_KEY is in your .env file.")
                with st.expander("Show Technical Error"):
                    st.write(e)