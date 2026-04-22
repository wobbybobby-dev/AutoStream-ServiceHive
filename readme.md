# AutoStream AI Agent

A conversational AI lead-capture agent for AutoStream, built with LangGraph + Claude 3 Haiku.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_key_here
```

Run the terminal demo:
```bash
python main.py
```

## Architecture 

This agent is built with **LangGraph** because it provides explicit, inspectable state management — every field (lead info, conversation history, intent, RAG context) lives in a typed `AgentState` dict that flows through the graph. This makes debugging easy and the state visible at any point. LangGraph also separates concerns cleanly: each node (retrieve → llm → update_lead → tool_call → update_history) does one job, making the pipeline easy to extend.

**State management**: The agent uses LangGraph’s TypedDict-based state to maintain conversation context across turns. The full conversation history is kept as a list of `HumanMessage` / `AIMessage` objects in `AgentState.messages`, passed to the LLM on every turn. This gives the model memory across 5–6+ turns with no external store needed. Lead info (`name`, `email`, `platform`) is accumulated incrementally across turns in `AgentState.lead_info`. The LLM indicates which field has been collected via lead_field_collected, and the system extracts the corresponding value from user input using lightweight parsing logic (e.g., regex for email).
This approach enables controlled multi-turn interactions and stateful decision-making while keeping the system simple and self-contained.

**RAG**: A keyword-scoring retrieval function chunks the knowledge base JSON into labelled text segments and scores them against the user query. No vector DB is needed at this scale. The top-3 chunks are injected into the system prompt each turn.

**Tool calling**: `mock_lead_capture()` is guarded by a `lead_captured` flag and only fires when all three lead fields are present and the LLM signals `trigger_lead_capture: true`.

## WhatsApp Deployment via Webhooks

1. **Receive messages**: Register a WhatsApp Business API webhook URL (e.g., via Twilio or Meta's Cloud API). Every incoming message hits your endpoint as a POST request with the sender's phone number and message text.
2. **Route to agent**: Your server looks up (or creates) a session for that phone number, loads the persisted `AgentState` from a store (Redis or a DB), and calls `run_turn(graph, state, user_input)`.
3. **Persist state**: After each turn, serialise the updated `AgentState` (JSON-serialisable) back to the store keyed by phone number. This preserves conversation history across sessions.
4. **Reply**: Use the WhatsApp API to send `agent_reply` back to the user's number.
5. **Lead capture**: `mock_lead_capture()` gets replaced with a real CRM API call — the rest of the agent logic stays identical.

## Project Structure

```
autostream_agent/
├── local_database.json   # AutoStream product data (RAG source)
├── prompts.py            # System prompt + intent examples
├── rag.py                # Retrieval logic
├── tools.py              # mock_lead_capture + tool registry
├── agent.py              # LangGraph state machine
├── main.py               # Terminal chat loop
└── requirements.txt
```
