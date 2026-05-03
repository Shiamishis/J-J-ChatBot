1. Too many LLM queries
2. Add one more layer to decide what type of question is
3. Make the 3 dashboards
4. Somehow know what to do with difficult questions, i.e. "Why did this KPI regress last month?"
5. Check metadata of the dashboard
6. System to create ticket (when create ticeket - what questions, if the LLM is unsure)
7. Document best practices for LLM integration
8. Ask about LLM budget (current limited GROQ API credits)
9. The A), B) and C) sections are doable, look into solving the rest of the sections
10. Add premium feature

Who does what:
1. Andreas: backend; make the scripts run as a whole 
2. Andrei: Dashboard and integration of LLM within it (powerapp to create the chatbot interface, power automate backend of powerapp, hierarchy: Powerautomate -> Powerapp -> PowerBI)


Frontend: make pretty, add context awareness, history (Andrei)
Backend: handlers, session(Andreas) 

Microsoft Questions:
1. How to make the app context aware?
2. How to integrate best a power app within power bi so it is pretty
3. How to publish a power app within a company





Common Questions:
Below are the categories of questions we most commonly see, with examples phrased the way users naturally ask them. 

 

A) “What is…” / metric definition questions (semantic layer)

“What does [metric] mean exactly?”
“How is [KPI] calculated in the dashboard?”
“Which data/table/field is the source of [KPI]?”
Why it matters: these are not SQL queries; they’re semantic/metadata answers. Your bot will need a metric glossary and governance-approved definitions.

 

B) “Show me…” / retrieval & slicing questions (straight SQL)

“Show me trend of [KPI] by month for the last 12 months.”
“Break down [KPI] by region / product / customer segment.”
“Top 10 brands by [KPI] this quarter.”
“Compare this quarter vs. last quarter for [KPI].”
Why it matters: these drive predictable GROUP BY, ORDER BY, time filters, and joins.

 

C) Diagnostic / “Why did it change?” questions (needs decomposition) => this is where it gets more complex because you’ll need more context. We don’t expect you to have time to deliver answers to these type of questions, 

“Why did [KPI] drop last month?”
“What drove the increase in Region A?”
“Is the change due to volume, mix, or price?”
Why it matters: you’ll want either (1) pre-modeled decomposition views, or (2) a guided analysis flow that runs multiple queries.

 

D) Data quality & refresh questions (operational trust)

“When was this dashboard last refreshed?”
“Why doesn’t this number match the report I exported last week?”
“Are there missing values for [field]?”
“Which source system did this come from?”
Why it matters: you need pipeline metadata (refresh timestamps, lineage, versioning) accessible to the bot.

 

E) Navigation & “How do I…” questions (dashboard UX)

“Where do I find [metric] in the dashboard?”
“How do I filter to only active customers?”
“What does this filter do?”
“Why is this visual blank when I select X?”
Why it matters: these are best solved by a dashboard knowledge base (RAG over documentation + screenshots/alt text + curated Q&A), not SQL.

 

F) Permissions & access questions (governance)

“Why can’t I see Region B?”
“Can I export row-level data?”
“Who has access to this dashboard?”
Why it matters: requires integration with entitlements and a safe response policy.

 

I) Data & dashboard issues 

“The numbers in this dashboard look incorrect—how can I report an issue?”
“This visual is blank or not loading after applying filters.”
“The dashboard hasn’t refreshed—can someone check the data pipeline?”
“Can we add a new filter or dimension to this dashboard?”
“Can I log a question for the data team?”

Ideally, you would implement a simple flow where tickets or requests are logged in a central repository (for example, an Excel file).


3) Due to the relational nature of the data and the pre-defined schema, we were considering a text-to-SQL RAG implementation. Does this approach align with your current model and technical expectations for the project?
