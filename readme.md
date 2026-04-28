

# 🛡️ Enterprise ITSM Agentic Orchestrator

An autonomous, event-driven IT Service Management (ITSM) platform built with **LangGraph**. This system moves beyond simple chatbots, implementing a multi-agent workflow to automate enterprise ticket triage, strict ITIL classification, zero-trust security routing, and automated resolution via a self-healing RAG pipeline.

Built to demonstrate scalable architecture, risk mitigation, and agentic workflows for enterprise environments.

## ✨ Key Architectural Features

* **Zero-Trust Agentic Routing:** Implements hard fail-safes. Routine access requests bypass expensive database lookups and route directly to automation mocks. Critical infrastructure problems and security breaches are mathematically quarantined and forced to human escalation, preventing LLM hallucinations in high-risk scenarios.
* **Continuous Learning RAG Pipeline:** Utilizes an LLM-as-a-Judge node. If the AI successfully resolves a ticket and passes strict safety validation, the resolution is automatically embedded back into **ChromaDB**. The system organically gets smarter with every resolved ticket.
* **Dual-Sided ITSM Command Center:** A headless backend architecture wrapped in an asynchronous **Streamlit** dashboard. Includes a simulated email ingestion portal for users and a live Kanban/Audit dashboard for human IT agents powered by **SQLite**.
* **Production Observability:** Natively integrated with **LangSmith** for live execution latency and token telemetry. Evaluated using the **RAGAS** framework to mathematically verify Context Precision, Answer Relevancy, and Faithfulness.
* **Fault Tolerance:** Utilizes LangGraph's `MemorySaver` checkpointer to implement exponential backoff and automatic state resumption if LLM API rate limits are hit during execution.

---

## 🔄 Deep Dive: The Agentic Workflow (Knowledge Transfer)
<img width="571" height="729" alt="image" src="https://github.com/user-attachments/assets/5ed3573e-e78f-4efa-a2b7-7f6d6319ad05" />

The core orchestration of this platform relies on a deterministic state graph powered by LangGraph. Rather than relying on a single unpredictable LLM prompt, the system passes an `AgentState` object through specialized, isolated nodes. 

Here is the exact lifecycle of a ticket traversing the architecture:

### Phase 1: Ingestion & Preprocessing (Node 1)
* **The Action:** The system intercepts a raw incoming email/ticket and initializes the global state dictionary.
* **PII Redaction:** Before any data touches the vector database or routing logic, a specialized LLM agent parses the text and strips Personally Identifiable Information (PII). 
* **Enterprise Value:** Ensures GDPR/HIPAA compliance from step zero, preventing sensitive user data from being permanently embedded in historical logs.

### Phase 2: Strict ITIL Classification (Node 2)
* **The Action:** The redacted text is evaluated using strict JSON structured outputs.
* **The Logic:** The LLM maps the unstructured text into standardized IT Infrastructure Library (ITIL) fields:
  * `Queue`: (e.g., Technical Support, HR, Billing).
  * `Ticket Type`: Strict definitions (Incident, Request, Problem, Major Security Event).
  * `Priority`: (Low, Medium, High, Critical).
  * `Confidence Score`: A float (0.0 - 1.0) measuring the LLM's certainty.
* **Enterprise Value:** Transforms unstructured human panic into structured, queryable data.

### Phase 3: The Zero-Trust Router (Dynamic Edge)
* **The Action:** A programmatic Python function evaluates the Node 2 metadata and directs the graph to one of three specialized branches.
* **The Logic Gates:**
  1. **🚨 Quarantine Route (Escalate):** If `Type == "Security"` OR `Priority == "Critical"` OR `Confidence < 0.70`, the AI immediately stops processing and routes to a human. *Why?* To prevent the AI from hallucinating a response to an active cyberattack or taking action when uncertain.
  2. **⚙️ Automation Route (Tool Call):** If `Type == "Request"` (e.g., "I need a software license"), it bypasses the vector database and triggers a mocked API extraction. *Why?* Database vector queries are computationally expensive. Routine access requests don't require historical troubleshooting; they require API provisioning.
  3. **📚 Standard Route (RAG):** If it is a standard `Incident` (Break/Fix), it is routed to the vector database.

### Phase 4: Metadata-Filtered RAG (Node 3)
* **The Action:** The system queries **ChromaDB** for historical solutions to similar tickets.
* **The Architecture:** It doesn't just do a blind semantic search. It dynamically injects the `Queue` classified in Node 2 as a `WHERE` clause in the vector search.
* **Enterprise Value:** Eliminates cross-departmental hallucinations. A "Technical Support" database error will never accidentally pull up an "HR Payroll" database fix, heavily increasing Context Precision.

### Phase 5: Generation & LLM-as-a-Judge (Nodes 4 & 5)
* **Generation:** An LLM synthesizes the user's issue with the retrieved ChromaDB context to draft a tailored, step-by-step resolution.
* **Validation (The Judge):** The drafted resolution is NOT sent to the user immediately. It is passed to a secondary, low-temperature LLM programmed as a strict validator. It evaluates the draft for *Accuracy*, *Completeness*, and *Safety*. If it fails, the `final_status` is marked as escalated.

### Phase 6: The Audit Sink & Continuous Learning (Node 6)
* **The Audit Log (SQLite):** Every single execution path converges at this sink node. The complete state—whether successfully resolved or escalated to humans—is committed to a relational SQLite database. This powers the live Streamlit IT Agent Dashboard.
* **Self-Healing Loop (ChromaDB):** If and ONLY if a ticket meets three strict criteria:
  1. It was auto-resolved successfully.
  2. It passed the LLM-as-a-Judge safety validation.
  3. It was NOT flagged as a Security/Critical risk.
  ...then the system takes the newly generated fix and permanently embeds it back into the ChromaDB vector space. The AI organically expands its own knowledge base securely.

---

## 🛠️ Tech Stack

* **Orchestration:** LangGraph, LangChain
* **LLM:** Cerebras (qwen-3-235b-a22b-instruct)
* **Vector Database:** ChromaDB (all-MiniLM-L6-v2 embeddings)
* **Relational Database:** SQLite (Audit Logging & State Persistence)
* **Observability & Eval:** LangSmith, RAGAS Framework
* **Frontend UI:** Streamlit

## ⚙️ Installation & Setup

Currently, this project runs locally via a Python virtual environment. 

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/your-repo-name.git](https://github.com/yourusername/your-repo-name.git)
   cd your-repo-name
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database Setup (Cloud Download):**
   *Note: Because the initialized vector databases exceed GitHub's file limits, a download script is provided to fetch the seed data.*
   ```bash
   python setup_db.py
   ```

5. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your API keys:
   ```env
   CEREBRAS_API_KEY="your_cerebras_key"
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_ENDPOINT="[https://api.smith.langchain.com](https://api.smith.langchain.com)"
   LANGCHAIN_API_KEY="your_langsmith_key"
   LANGCHAIN_PROJECT="ITSM_Agent_Production"
   ```

6. **Run the Command Center:**
   ```bash
   streamlit run app.py
   ```

## 🧪 Demo Scenarios

To test the routing intelligence, simulate the following emails in the Streamlit sidebar:

* **Routine Automation (Cost Optimization):**
  * **Subject:** `Need Adobe Creative Cloud License`
  * **Body:** `I transferred to Marketing and need Adobe Acrobat Pro assigned to j.smith@company.com.`
  * **Result:** Bypasses RAG, routes to automated provisioning mock.

* **Zero-Trust Quarantine (Risk Mitigation):**
  * **Subject:** `Unauthorized root access detected`
  * **Body:** `We detected privilege escalation on a production server. Possible breach.`
  * **Result:** Blocked from Continuous Learning, instantly escalated to human SecOps triage.

## 🚀 Future Roadmap

This project is actively being developed to transition from a simulated orchestration engine into a fully deployable enterprise tool. Upcoming features include:

* **Agentic Tool Execution (Real APIs):** Upgrading the automation node to execute real Python tool calls to external APIs (e.g., Active Directory/Okta for provisioning, Jira for ticket creation) instead of generating mocked system logs.
* **SMTP Integration:** Connecting the resolution node to an SMTP server (like SendGrid or AWS SES) to dispatch actual automated email responses to the end-users who submitted the tickets.
* **Containerization:** Packaging the entire architecture (Python environment, ChromaDB volumes, and SQLite persistence) into Docker and `docker-compose` for seamless cloud deployment (AWS EC2 / Azure).
  
