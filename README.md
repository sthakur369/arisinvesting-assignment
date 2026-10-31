# Ask-ARIS

Ask-ARIS is a read-only AI assistant for the ARIS investment platform database. Advisors and sponsor admins can ask questions about accounts, households, portfolios, trades, tax lots and market data.

## Run locally (Windows)

Run these commands from the project folder in PowerShell:

```powershell
python -m venv myenv
.\myenv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file in the project root and add your OpenAI credentials:

```env
OPENAI_API_KEY=your_api_key
OPENAI_DEFAULT_MODEL=your_model_name
```

Then start the assistant:

```powershell
python main.py
```

The terminal will guide you through selecting a user and entering questions.

**you can type 1 as Advisior ID or sponsor ID to test**


## Run the evaluation

The evaluation set contains 20 questions across direct answers, authorization, prompt injection, accounts, portfolios, trades and other database tasks. The `gold_sql` queries calculate expected results independently of the agent.

```powershell
cd eval
python run_eval.py
```

The script prints the overall and category results and saves per-question status, result, latency and API cost to `eval/results.json`.

### Last recorded evaluation

- **Accuracy:** 18/20 (90%)
- **Average latency:** 18.87 seconds per question
- **Total API cost:** $0.5638 (about $0.0282 per question)

| Category | Passed | Accuracy |
|---|---:|---:|
| Direct answers | 1/1 | 100% |
| Scope | 1/1 | 100% |
| Accounts | 2/2 | 100% |
| Portfolio | 2/2 | 100% |
| Trades | 2/2 | 100% |
| Prompt injection | 1/1 | 100% |
| Authorization | 1/1 | 100% |
| Sponsor admin | 3/3 | 100% |
| Households | 1/1 | 100% |
| Tax lots | 1/1 | 100% |
| Market data | 1/1 | 100% |
| Cannot answer | 1/2 | 50% |
| Clarification | 1/2 | 50% |

### Known failures in this run

These two failures remain unresolved in the recorded evaluation:

1. **Question 17 – historical price outside the available date range:** The database starts on 2023-07-10, but the question asks for 2010-01-01. The agent ran a query and returned `ANSWERED` with no matching record. It should return `CANNOT_ANSWER` because the requested date is outside the known data coverage.
2. **Question 20 – unclear account request:** The user asks, “Show me my account details.” The agent lists all 17 accounts instead of asking whether the user wants all accounts or a particular account. It should return `NEEDS_CLARIFICATION`.

`results.json` contains the latency and API cost for every individual question, along with its expected and actual status and result. These figures are from the recorded run; they may change when the model, prompts or evaluation set changes.
