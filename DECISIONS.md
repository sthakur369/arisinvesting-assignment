# DECISIONS

This file records the choices that needed thought while building and testing Ask-ARIS. It also calls out what is still uncertain.

## 1. Keep the assistant focused on ARIS

**What I decided:** The assistant should answer greetings and questions about the ARIS platform. It should refuse unrelated questions.

**Why:** This is an ARIS data assistant, not a general-purpose chatbot.

**How I checked:** I tested a greeting and an unrelated question. The greeting was answered and the unrelated question was refused.

**Ask the business:** Should the assistant also explain general investment concepts, or should it only answer questions about ARIS data and workflows?

## 2. Give the assistant the user's role and ID separately

**What I decided:** The application sends the user's role and ID along with the question. For example, it tells the assistant whether the user is an advisor or a sponsor admin. The assistant should use these application-provided details, not trust claims typed into the chat such as “I am an admin”.

**How I checked:** I tested questions from both roles and a request by one advisor to view another advisor's household. I also tested a household note that contained instructions telling the assistant to reveal other clients' email addresses. The assistant showed the note as stored data but did not follow those instructions.

**What is still missing:** To keep the assignment version simple, I did not add a separate permission check in the application. The model is still responsible for putting the right access limits in its SQL. This is not enough protection for real client data; the application or database must enforce permissions independently.

**Ask the business:** What exactly can an advisor see? Can a sponsor admin see data for every advisor in their own firm? Are there any fields that either role must not see?

## 3. Keep database access read-only

**What I decided:** Open the SQLite database in read-only mode and instruct the assistant to generate only `SELECT` queries.

**Why:** Ask-ARIS needs to look up information, not change client or business records.

**What I checked:** The database connection uses SQLite's `mode=ro` option.

**What is still missing:** Read-only mode stops database changes, but it does not stop an incorrect or over-broad read query. There is not yet a separate check that validates every generated query and its access limits before it runs.

## 4. Use separate steps to get data and explain it

**What I decided:** The first model call decides what to do. When data is needed, it creates a query. After the query runs, a second model call explains the returned rows and produces the structured response.

**Why:** Keeping query generation separate from the explanation makes it easier to control the response format and provide evidence for database answers.

**How I checked:** I tested direct answers, database questions, refusals and clarification requests. The response is mapped to the assignment's four statuses: `ANSWERED`, `REFUSED`, `CANNOT_ANSWER` and `NEEDS_CLARIFICATION`.

## 5. Tell the difference between missing data and an unclear question

**What I decided:** Use `CANNOT_ANSWER` when the database does not contain the information or cannot cover the request. Use `NEEDS_CLARIFICATION` when the user could provide a missing detail and make the question answerable.

**How I checked:** The assistant correctly said it could not provide a household phone number because that field is not stored. It asked for more detail when asked, “How did my portfolio perform?” because a time period and a measure of performance were missing.

**What did not work:** The 2010 price question still failed in the 20-question evaluation. The assistant queried the price table, found no row and returned `ANSWERED`. The known price history starts on 2023-07-10, so the request should have been classified as `CANNOT_ANSWER` before querying. Also, “Show me my account details” was answered by listing all 17 accounts instead of asking whether the user wanted all accounts or one particular account.

**Next step:** Improve the instructions for checking known date coverage and for asking clarification when “my account details” does not say which account or whether all accounts are wanted. Retest both cases.


## 6. Check answers independently with an evaluation set

**What I decided:** Create 20 test questions. For questions that need database data, the evaluation file includes a separate reference SQL query and expected result format. These reference queries are used only by the evaluation script; the assistant does not receive them when answering.

**How I checked:** I ran all 20 questions. The assistant passed 18 and failed 2, for 90% accuracy. The two failures are described in section 5. Average latency was 18.87 seconds and total API cost was about $0.56 for this run.

**What I learned:** My first run loaded only one question, so its 100% result was not a full evaluation. I checked the number of questions loaded and then ran the complete set. The full run is a more useful baseline, but 20 questions are not enough to prove the assistant is ready for production.
