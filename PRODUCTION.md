# PRODUCTION

Ask-ARIS is an assignment prototype, not yet safe to use with real advisor or client data. These are the main things that must be in place before launch.

## What must be ready before launch

- **Verify who is using it.** Connect the assistant to real sign-in. Get the user's role and ID from the authenticated session, not from what they type in the chat.
- **Enforce access outside the AI model.** Check every query against the user's permissions before it reaches the database. Do not rely on the model or its prompt to protect one advisor's data from another.
- **Check every SQL query before running it.** Allow only approved read queries, apply access limits, bind query values safely, and set limits on query time and returned rows. Keep the database read-only.
- **Agree on financial calculations.** Have the business confirm how portfolio value and unrealized P&L should be calculated, including snapshot dates and missing or incomplete cost-basis data. Resolve the P&L difference found during testing.
- **Test more than the happy path.** Expand the evaluation set and test access restrictions, prompt-injection attempts, missing data, unclear questions, empty results and dates outside the database's coverage. Review each failure.
- **Better model for advance queries** current model is luna which is cost effective

## What I would not ship yet

- AI-generated SQL that runs without a separate query and permission check.
- Portfolio or tax figures until the business has approved the calculation rules.
