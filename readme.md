
# 🛡️ Enterprise ITSM Agentic Orchestrator

An autonomous, event-driven IT Service Management (ITSM) platform built with **LangGraph**. This system moves beyond simple chatbots, implementing a multi-agent workflow to automate enterprise ticket triage, strict ITIL classification, zero-trust security routing, and automated resolution via a self-healing RAG pipeline.

Built to demonstrate scalable architecture, risk mitigation, and agentic workflows for enterprise environments.

## ✨ Key Architectural Features

* **Zero-Trust Agentic Routing:** Implements hard fail-safes. Routine access requests bypass expensive database lookups and route directly to automation mocks. Critical infrastructure problems and security breaches are mathematically quarantined and forced to human escalation, preventing LLM hallucinations in high-risk scenarios.
* **Continuous Learning RAG Pipeline:** Utilizes an LLM-as-a-Judge node. If the AI successfully resolves a ticket and passes strict safety validation, the resolution is automatically embedded back into **ChromaDB**. The system organically gets smarter with every resolved ticket.
* **Dual-Sided ITSM Command Center:** A headless backend architecture wrapped in an asynchronous **Streamlit** dashboard. Includes a simulated email ingestion portal for users and a live Kanban/Audit dashboard for human IT agents powered by **SQLite**.
* **Production Observability:** Natively integrated with **LangSmith** for live execution latency and token telemetry. Evaluated using the **RAGAS** framework to mathematically verify Context Precision, Answer Relevancy, and Faithfulness.
* **Fault Tolerance:** Utilizes LangGraph's `MemorySaver` checkpointer to implement exponential backoff and automatic state resumption if LLM API rate limits are hit during execution.

## 🔄 The Agentic Workflow (How it Works)
<img width="571" height="729" alt="image" src="https://github.com/user-attachments/assets/5ed3573e-e78f-4efa-a2b7-7f6d6319ad05" />

The core of this platform is a deterministic state graph powered by LangGraph. When a user submits an email/ticket, it traverses the following node pipeline:

1. **Intake & PII Redaction (Node 1):** The raw email is intercepted. An LLM scans and strips Personally Identifiable Information (PII) to ensure data compliance before further processing.
2. **Enterprise ITIL Classification (Node 2):** The redacted ticket is analyzed using structured outputs to extract ITIL-standard metadata: `Queue` (e.g., Technical Support), `Ticket Type` (Incident, Request, Problem, Security), `Priority`, `Language`, and an AI `Confidence Score`.
3. **The Zero-Trust Router (Dynamic Edge):** A programmatic router evaluates the classification data to determine the safest execution path:
   * 🛡️ *Quarantine Route:* If the ticket is a "Major Security Event" or has "Critical" priority, it instantly routes to Human Escalation.
   * 🤖 *Automation Route:* If it is a routine "Request" (e.g., software license) or a "Mass Outage", it routes to an Agentic Tool-Calling node to mock an API execution, saving database compute costs.
   * 📚 *Standard Route:* If it is a standard "Incident", it routes to the RAG pipeline.
4. **Metadata-Filtered RAG (Node 3):** For standard incidents, the system queries **ChromaDB**. It uses the `Queue` predicted in Node 2 as a strict metadata filter, ensuring the AI only retrieves historical fixes from the correct department to eliminate cross-departmental hallucinations.
5. **Generation & Resolution (Node 4):** The LLM synthesizes the retrieved historical context and drafts a step-by-step resolution tailored to the user.
6. **LLM-as-a-Judge Validation (Node 5):** A secondary, low-temperature LLM strictly evaluates the proposed resolution for safety, accuracy, and completeness. If it fails validation, it is escalated to a human.
7. **The Audit Sink & Continuous Learning (Node 6):** Regardless of the outcome, the final state is logged to a **SQLite** database for the human Helpdesk Dashboard. If the ticket was successfully auto-resolved, safe, and not quarantined, the fix is embedded back into ChromaDB for future use.

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
   *Note: Because the initialized vector databases exceed GitHub's file limits, a download script is provided.*
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
