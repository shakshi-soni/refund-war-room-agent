Refund War Room

An evidence-backed refund investigation agent that answers operational questions using a synthetic orders/refunds database and internal policy documents.

1. Summary

Refund investigations often require information from multiple sources. A database can provide transaction counts, while policy documents explain the rules that apply to a particular date. Using only one source can produce incomplete or incorrect answers.

Refund War Room combines read-only SQL queries and document retrieval to investigate questions, attach evidence to factual claims, and abstain when the available evidence is insufficient or conflictin

2. Architecture

problem-2/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── generate_data.py
├── run_eval.py
├── data/
│   ├── bazaar.db
│   ├── eval_questions.json
│   └── docs/
├── agent/
│   ├── state_machine.py
│   ├── verifier.py
│   ├── conflict_policy.py
│   ├── injection_gate.py
│   └── schema.py
├── tools/
│   ├── sql_tool.py
│   ├── doc_tools.py
│   ├── whatsapp_tool.py
│   └── fault_wrapper.py
├── tests/
│   ├── test_verifier.py
│   └── test_injection_gate.py
└── logs/
    └── whatsapp_log.txt

3. Setup

Requirements

Python 3

pip

A terminal

The project files in this repository

No external LLM API key is required for the rule-based implementation described here.

Create a virtual environment

Windows PowerShell:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt


5. How to run

Run the interactive agent:

python -m agent.state_machine

Enter a question at the prompt. Type exit to stop the session.

Run the verifier tests:

python -m pytest tests/test_verifier.py -v

Run the complete test suite:

python -m pytest tests/ -v

Run the evaluation:

python run_eval.py

7. Design decisions and trade-offs

Rule-based planning

The current implementation uses explicit routing rules rather than relying on an LLM to decide every action. This makes the workflow easier to inspect and reproduce, but keyword-based routing can miss differently worded questions or questions that require more complex reasoning.

Read-only SQL

Database access is restricted to investigation queries. This reduces the risk of changing synthetic records while answering questions. The safety checks must reject write operations and multiple statements while permitting valid read-only queries.

Evidence-backed claims

Factual claims should cite the document quotation or SQL result that supports them. SQL evidence includes a result hash so that the verifier can detect a mismatch between the cited hash and the returned rows.

A hash establishes result integrity within this workflow; it does not, by itself, establish that a claim follows logically from those rows.

Policy conflicts and effective dates

Policy documents can change over time. The agent should evaluate the requested date, identify applicable versions, and apply an explicit precedence rule only when the available metadata supports it. If the rule cannot determine which policy governs, the agent should surface the conflict rather than silently choose a version.

8. Known limitations and failure cases
