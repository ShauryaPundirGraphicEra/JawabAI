 
from functools import lru_cache

from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Annotated,List,Optional,Any,Literal
from pydantic import Field
from langchain_core.messages import HumanMessage,SystemMessage,BaseMessage
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
import os

import sqlite3
from datetime import datetime
from langchain_cerebras import ChatCerebras
 

load_dotenv()

try:
    from node_logging import setup_database
except ImportError:
    def setup_database():
        pass
 


llm = ChatCerebras(
    model="qwen-3-235b-a22b-instruct-2507",
    api_key=os.getenv("CEREBRAS_API_KEY"),
    temperature=0.4,
)




 
from chromadb.utils import embedding_functions
import chromadb

# 1. INITIALIZE ONCE (Global Scope)
@lru_cache
def initialize_res():
    print("Loading embedding model into memory...")
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(
        name="ticket_history",
    )
    print("Model and DB ready!")
    return collection

collection = initialize_res()
class AgentState(TypedDict):
    # 1. Intake Data 
    ticket_id: str
    original_title: str
    original_description: str
    
    # 2. PII Redaction (Node 1) 
    redacted_title: Optional[str]
    redacted_description: Optional[str]
    
    # 3. Classification & Routing Logic (Node 2 & Routers) ---
    queue: Optional[str]
    ticket_type: Optional[str]
    priority: Optional[str]
    category: Optional[str] 
    confidence_score: Optional[float]
    is_repeated_issue: bool
    
    # 4. RAG & Automation Retrieval (Node 3B & 3C) 

    retrieved_contexts: List[str] 
    automation_suggestion: Optional[str]
    
    # 5. Generation (Node 4) 
    proposed_resolution: Optional[str]
    
    # 6. Validation / LLM-as-a-Judge (Node 5) 
    validation_passed: Optional[bool]
    validation_feedback: Optional[str] 
    
    # 7. Final Output & Logging (Node 6A/6B)
    final_status: Optional[str]  
 
class RedactionResult(TypedDict):
    redacted_title: str
    redacted_description: str


def redactPII(state:AgentState)->AgentState:
    
    # Redact PII from orignal title and description using llm
    print("Redacting PII from the ticket...")
    prompt=f"""You are a helpful assistant working for microsoft customer service ,for redacting personally identifiable information (PII) from IT support tickets.
        Given the following ticket details, please redact any PII while preserving the overall context and meaning of the ticket for accurate classification and resolution.
        Original Title: {state.get('original_title')}
        Original Description: {state.get('original_description')} """
    format_llm=llm.with_structured_output(RedactionResult)
    response=format_llm.invoke(prompt)
    #return {'redacted_title':'NO','redacted_description':'Yes gfhkvh '}
    print(response)
    return {'redacted_title':response['redacted_title'],'redacted_description':response['redacted_description']}



 
class ClassificationResult(TypedDict):
    queue: Literal[
        "Technical Support", "Customer Service", "Billing and Payments", 
        "Product Support", "IT Support", "Returns and Exchanges", 
        "Sales and Pre-Sales", "Human Resources", "Service Outages and Maintenance", "General Inquiry"
    ] = Field(description="The department the ticket should be routed to.")
    
    ticket_type: Literal["Incident", "Request", "Problem", "Change"] = Field(
        description="Incident (unexpected break/fix), Request (routine inquiry/access), Problem (underlying systemic issue), Change (planned update)."
    )
    
    priority: Literal["low", "medium", "high", "critical"] = Field(
        description="Urgency of the issue."
    )
    confidence_score: float = Field(
        description="Confidence level in your classification, from 0.0 to 1.0."
    )
    
    is_repeated_issue: bool = Field(
        description="DEFAULT TO FALSE. Set to True ONLY if the ticket explicitly mentions a mass company-wide outage affecting multiple users (e.g., 'system is down for everyone'). A single user's swollen battery or slow query is FALSE."
    )


def classify(state:AgentState)->AgentState:
    conn = sqlite3.connect('itsm_portal.db')
    cursor = conn.cursor()

    cursor.execute("SELECT original_description FROM tickets WHERE datetime(timestamp) >= datetime('now', '-1 hour') ")

    rows = cursor.fetchall()
    
    recent_issues = [r[0] for r in rows]

    formatted_rows = "\n".join(
        f"- {desc}" for desc in recent_issues[:20]
    )
    
    print("Classifying the ticket into the appropriate category...")
    prompt=f"""You are an expert Enterprise IT Service Management (ITSM) classifier working for microsoft customer service.
    Analyze the following redacted ticket and extract the routing metadata.
    CRITICAL RULES:
    1. queue MUST be one of the exact specified literal values.
    2. ticket_type must strictly follow ITIL definitions:
       - Incident: Something is broken and needs fixing.
       - Request: Asking for software, hardware, information, or access.
       - Problem: A severe, recurring underlying issue.
       - Change: Requesting a modification to infrastructure.
    3. priority: Determine urgency (low, medium, high, critical).
    4. is_repeated_issue MUST be False unless a massive multi-user outage is explicitly described u can see it in {formatted_rows} which have the 
    recently solved tickets ,you check these last 1 hour tickets and then decide accordingly.
    Title: {state.get('redacted_title')}
    Description: {state.get('redacted_description')}"""
    classify_llm=llm.with_structured_output(ClassificationResult)
    response=classify_llm.invoke(prompt)
    
    
    return {'queue': response['queue'],
        'ticket_type': response['ticket_type'],
        'priority': response['priority'],
        'confidence_score':response['confidence_score'],
        'is_repeated_issue':response['is_repeated_issue']}
 

def escalate_node(state: AgentState)->AgentState:
    """
    Node 3A: Triggered when confidence is low. Bypasses generation and goes to human review.
    """
    print(f"--- [NODE 3A] ESCALATING TO HUMAN TRIAGE ---")
    
    reason = "Confidence score below threshold."
    status = f"ESCALATED: {reason}"
    
    return {
        "final_status": status,
        "proposed_resolution": "This issue requires human intervention. Routed to L2 Support."
    }

def automation_suggestion_node(state: AgentState)->AgentState:
    """
    Node 3B: Triggered when a repeated systemic issue (like a mass outage) is detected.
    """
    print(f"--- [NODE 3B] MASS OUTAGE / REPEATED ISSUE DETECTED ---")
    
    if state.get("is_repeated_issue"):
        resolution = "We are currently tracking a widespread company outage related to this service. Engineering is engaged. This ticket has been automatically linked to the Master Incident."
        return {
            "proposed_resolution": resolution,
            "final_status": "RESOLVED_AUTO" # Explicitly sets the status for the DB
        }

    # SCENARIO 2: Access/Software Request (Agentic Tool Calling Mock)
    if state.get("ticket_type") == "Request":
        print("Mocking API Tool Call for Access Provisioning...")
        return{
            "proposed_resolution": "Your request for access/software has been processed. You should receive an email confirmation shortly. If you need immediate assistance, please contact our helpdesk directly.",
            "final_status": "RESOLVED_AUTO"
        }
    
    

    return {
        "proposed_resolution": "Automated routing failed to match a specific rule.",
        "final_status": "ESCALATED_SYSTEM_ERROR"        
        }
 

def retrieve_context(state: AgentState) -> AgentState:
    print("Retrieving relevant context using Metadata Filtering...")

    query = state.get('redacted_description', "")
    queue = state.get('queue') # Extract the department predicted by Node 2
        
    # Beast Level: Filter ChromaDB by the exact department queue!
    try:
        # If the LLM successfully predicted a queue, use it as a strict filter
        where_clause = {"queue": queue} if queue and queue != "Unknown" else None
        
        results = collection.query(
            query_texts=[query],
            n_results=3,
            where=where_clause
        )
        documents = results['documents'][0] if results['documents'] else []
        print(f"-> Retrieved {len(documents)} historical fixes from the '{queue}' queue.")
        
    except Exception as e:
        print(f"-> ChromaDB Query Error: {e}")
        documents = []
    
    return {'retrieved_contexts': documents}



def generate_resolution(state:AgentState)->AgentState:
    print("Generating a proposed resolution for the ticket...")
    contexts_list = state.get('retrieved_contexts', [])
    formatted_contexts = "\n".join([f"- {ctx}" for ctx in contexts_list])
    prompt=f"""You are an expert Enterprise IT Resolution Agent working for microsoft customer service.
    A user has submitted an IT ticket. 
    You have searched the company database and retrieved historical resolutions from similar past tickets.

    User's Redacted Issue:
    {state.get('redacted_description')}

    Historical Resolutions from similar past tickets:
    {formatted_contexts}

    Task:
    Write a clear, step-by-step resolution plan for the user. 
    Do NOT ask for more information. Base your fix strictly on the Historical Resolutions provided. 
    If the Historical Resolutions say 'Escalated', inform the user the ticket is being escalated.
    Format your response professionally as if communicating directly to the end user.
        """
    
    response=llm.invoke(prompt)
    
    return {'proposed_resolution':response.content}




def decide_route(state: AgentState) -> str:
    """
    Agentic routing logic with Zero-Trust Security Guardrails.
    """
    print(f"Determining routing for [{state.get('category')} | Type: {state.get('ticket_type')} | Priority: {state.get('priority')}]...")

    # 2. Immediate SecOps / Critical Escalation
    category = state.get("category", "")
    priority = state.get("priority", "")
    
    if category == "Security" or priority == "critical":
        print(f"-> Decision: ZERO-TRUST OVERRIDE. {priority.upper()} {category} event. Routing to Immediate Escalation.")
        return "escalate_node"
    
    # 3. Low Confidence (Safety First)
    confidence = state.get("confidence_score", 0.0)
    if confidence < 0.70:
        print(f"-> Decision: Low Confidence ({confidence}). Routing to Escalation.")
        return "escalate_node"

    ticket_type = state.get("ticket_type")

    # 4. ITIL Logic: Routine Requests
    if ticket_type == "Request":
        print("-> Decision: Routine Service Request. Routing to Access Automation.")
        return "automation_node" 
        
    # 5. ITIL Logic: Standard Problems
    if ticket_type == "Problem":
        print("-> Decision: Systemic Problem. Routing to L3 Escalation.")
        return "escalate_node"
    
     # 1. Mass Outage / Systemic Issue
    if state.get("is_repeated_issue"):
        print("-> Decision: Mass Outage Detected. Routing to Automation.")
        return "automation_node"
        

    # 6. Standard Incidents (Break/Fix)
    print("-> Decision: Standard Incident. Routing to RAG Troubleshooting.")
    return "rag_node"


# %%

class ValidationResult(TypedDict):
    validation_passed: bool=Field(description="True if the proposed resolution is valid and safe to communicate to the user, False otherwise.")
    validation_feedback: str=Field(description="Detailed feedback on any issues found with the proposed resolution, or 'No feedback provided.' if none.")
    final_status: Literal["RESOLVED_AUTO","ESCALATED_DUE_TO_FAILED_VALIDATION"]=Field(description="Final status of the ticket after validation, e.g., 'RESOLVED_AUTO' or 'ESCALATED_DUE_TO_FAILED_VALIDATION'.")
from langchain_cerebras import ChatCerebras


def validate_resolution(state:AgentState)->AgentState:
    print("Validating the proposed resolution...")
    llm2 = ChatCerebras(
    model="qwen-3-235b-a22b-instruct-2507",
    api_key=os.getenv("CEREBRAS_API_KEY"),
    temperature=0.1 
    )

    eval_llm = llm2.with_structured_output(ValidationResult)

    prompt = f"""You are an expert IT support validator working for microsoft customer service.
    A proposed resolution has been generated for a user's IT issue. 
    Your task is to critically evaluate the proposed resolution for accuracy, completeness, and safety before it is communicated to the user.

    User's Redacted Issue:
    {state.get('redacted_description')}

    Proposed Resolution:
    {state.get('proposed_resolution')}

    Validation Criteria:
    1. Accuracy: Does the resolution correctly address the user's issue based on the provided information?
    2. Completeness: Does the resolution include all necessary steps and information for the user to follow?
    3. Safety: Is there any risk of data loss, security issues, or further complications if the user follows this resolution?

    Provide a clear validation result (True/False) and detailed feedback on any issues found with the proposed resolution.
    """
    
    # 2. Invoke the strict judge
    response = eval_llm.invoke(prompt)

    return {
        "validation_passed": response['validation_passed'],
        "validation_feedback": response['validation_feedback'],
        "final_status": response['final_status']
    }


# %%


def log_ticket_node(state: AgentState) -> AgentState:
    """
    The final sink node. Logs everything to SQLite, and promotes verified fixes to ChromaDB.
    """
    print(f"--- [NODE 6] LOGGING TICKET {state.get('ticket_id')} ---")
    
    setup_database()
    
    # 1. ALWAYS write to SQLite for the Human Dashboard
    conn = sqlite3.connect('itsm_portal.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO tickets 
            (ticket_id, timestamp, queue, ticket_type, priority, original_description, proposed_resolution, final_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            state.get('ticket_id', 'UNKNOWN'),
            datetime.now().isoformat(),
            state.get('queue', 'Unassigned'),
            state.get('ticket_type', 'Unknown'),
            state.get('priority', 'Unknown'),
            state.get('original_description', ''),
            state.get('proposed_resolution', ''),
            state.get('final_status', 'UNKNOWN')
        ))
        conn.commit()
        print("-> Ticket logged to SQLite successfully.")
    except Exception as e:
        print(f"Database logging failed: {e}")
    finally:
        conn.close()
        
    # 2. CONTINUOUS LEARNING: Promote to ChromaDB ONLY if it was a successful, safe fix
    if state.get('final_status') == 'RESOLVED_AUTO' and state.get('validation_passed') == True:
        print(f" Verified Fix! Promoting {state.get('ticket_id')} to ChromaDB Knowledge Base...")
        try:
            doc_text = f"Subject: {state.get('original_title', '')} | Body: {state.get('original_description', '')}"
            
            collection.add(
                documents=[doc_text],
                metadatas=[{
                    "resolution": state.get('proposed_resolution', ''),
                    "queue": state.get('queue', ''),
                    "type": state.get('ticket_type', ''),
                    "priority": state.get('priority', ''),
                    "tags": "AI_Generated_Fix" # Tag it so you know it was auto-learned!
                }],
                ids=[state.get('ticket_id')]
            )
            print(f"-> Ticket promoted to ChromaDB successfully.")
        except Exception as e:
            print(f"ChromaDB promotion failed: {e}")

    return state


from langgraph.checkpoint.memory import MemorySaver

graph=StateGraph(AgentState)

graph.add_node('RedactPII',redactPII)
graph.add_node('Classify',classify)
# graph.add_node('decide_route',decide_route)
graph.add_node('escalate_node',escalate_node)
graph.add_node('automation_node',automation_suggestion_node)
graph.add_node('rag_node',retrieve_context)
graph.add_node('generate_resolution',generate_resolution)
graph.add_node('validate_resolution',validate_resolution)
graph.add_node('log_ticket', log_ticket_node)


graph.add_edge(START,'RedactPII')
graph.add_edge('RedactPII','Classify')
graph.add_conditional_edges('Classify', decide_route, {
    'escalate_node': "escalate_node",
    'automation_node': "automation_node",
    'rag_node': "rag_node"
})


graph.add_edge('rag_node','generate_resolution')
graph.add_edge('generate_resolution','validate_resolution')


graph.add_edge('escalate_node', 'log_ticket')
graph.add_edge('automation_node', 'log_ticket')
graph.add_edge('validate_resolution', 'log_ticket')


graph.add_edge('log_ticket', END)



# memory = MemorySaver()
# workflow=graph.compile(checkpointer=memory)

@lru_cache
def get_workflow():
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

workflow = get_workflow()

