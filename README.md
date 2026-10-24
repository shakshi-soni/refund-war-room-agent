# Refund War Room

An evidence-backed refund investigation agent. It answers operational questions using a synthetic orders/refunds database and internal policy documents.

## Summary

Refund questions need more than one source: the database gives counts, the policy docs give the rules for a given date. Using only one gives incomplete or wrong answers.

Refund War Room combines read-only SQL with document retrieval, attaches evidence to every factual claim, and abstains when evidence is insufficient or conflicting.

## Architecture

<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/7400b52a-51f8-46e0-b17e-683d6e8d49fe" />


## Setup

Requirements: Python 3, pip, a terminal. No LLM API key needed (rule-based).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## How to run

```powershell
python -m agent.state_machine            # interactive agent (type exit to quit)
python -m pytest tests/test_verifier.py -v   # verifier tests
python -m pytest tests/ -v               # full suite
python run_eval.py                       # evaluation
```

## Design decisions

- **Rule-based planning:** Explicit routing, easy to inspect and reproduce. Keyword routing can miss rephrased or complex questions.
- **Read-only SQL:** Rejects writes and multiple statements; allows valid read-only queries.
- **Evidence-backed claims:** Each claim cites a document quote or SQL result. SQL evidence carries a result hash so the verifier can catch mismatches. The hash proves integrity, not that the claim follows from the rows.
- **Policy conflicts:** The agent checks the requested date, finds applicable versions, and applies precedence only when metadata supports it. Otherwise it surfaces the conflict.

## Known limitations

- Keyword routing is brittle on paraphrased questions.
- No multi-step reasoning beyond the rules.
- SQL safety only covers known patterns.
- Tested on synthetic data only.

## AI-use note 

- for creating the fake database.
- upgrading the policy.
- draft the baseline SQL/schema to save time on boilerplate setup
- I treated the AI like an interactive documentation or query assistant to help map out the entity relationships faster
