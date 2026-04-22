"""
Core agent logic using LangGraph.

State machine:
  [user_input] → [retrieve_context] → [llm_call] → [parse_response] → [maybe_tool_call] → [reply]
                                                                              ↑
                                                                    loops back for next turn
                                                                    
State is persisted across turns via LangGraph's TypedDict state.
"""

import json
import os
import re
from typing import Annotated, TypedDict, Optional
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from prompts import SYSTEM_PROMPT, INTENT_EXAMPLES
from rag import retrieve_context
from tools import execute_tool


#state definition
class LeadInfo(TypedDict, total=False):
    name: Optional[str]
    email: Optional[str]
    platform: Optional[str]


class AgentState(TypedDict):
    messages: list
    user_input: str
    rag_context: str
    intent: str
    agent_reply: str
    lead_field_collected: Optional[str]
    trigger_lead_capture: bool
    lead_info: LeadInfo
    lead_captured: bool #prevents capturing same lead twice


#LLM setup
def get_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3
    )



#Graph nodes
def retrieve_node(state: AgentState) -> AgentState:               #returns relevant chunks from rag.py and saves to state dict
    context = retrieve_context(state["user_input"], top_k=3)
    return {**state, "rag_context": context}


def llm_node(state: AgentState) -> AgentState:
    llm = get_llm()

    #building context-enriched system message
    system_content = (
        f"{SYSTEM_PROMPT}\n\n"
        f"{INTENT_EXAMPLES}\n\n"
        f"## Current Lead Info Collected So Far\n{json.dumps(state['lead_info'], indent=2)}\n\n"
        f"## Relevant Knowledge Base Context\n{state['rag_context']}"
    )
    #reconstructing messages for this call
    messages = (
        [SystemMessage(content=system_content)]
        + list(state.get("messages", []))
        + [HumanMessage(content=state["user_input"])]
    )
    print("Calling LLM...")
    response = llm.invoke(messages)
    raw_text = response.content

    #parse JSON from the LLM response
    try:
        # Strip markdown code fences if present
        clean = re.sub(r"```(?:json)?|```", "", raw_text).strip()
        parsed = json.loads(clean)
    except Exception:
        # Fallback: treat the whole response as a plain message
        parsed = {
            "intent": "INQUIRY",
            "message": raw_text,
            "lead_field_collected": None,
            "trigger_lead_capture": False,
        }
    message = parsed.get("message", "")
    if isinstance(message, dict):
        message = str(message)

    return {
        **state,
        "intent": parsed.get("intent", "INQUIRY"),
        "agent_reply": message,
        "lead_field_collected": parsed.get("lead_field_collected"),
        "trigger_lead_capture": parsed.get("trigger_lead_capture", False),
    }


def update_lead_info_node(state: AgentState) -> AgentState:
    """
    Extract any newly collected lead field from the LLM response
    and accumulate it into lead_info.
    
    The LLM tells us which field it just collected via lead_field_collected.
    We then pull the actual value from the user's message using simple heuristics
    (for a more robust approach, you could ask the LLM to also return the value).
    """
    lead_info = dict(state["lead_info"])
    field = state.get("lead_field_collected")
    user_msg = state["user_input"].strip()

    if field == "name" and "name" not in lead_info:
        lead_info["name"] = user_msg
    elif field == "email" and "email" not in lead_info:
        # Extract email-looking token from message
        match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', user_msg)
        lead_info["email"] = match.group(0) if match else user_msg
    elif field == "platform" and "platform" not in lead_info:
        lead_info["platform"] = user_msg

    return {**state, "lead_info": lead_info}


def tool_node(state: AgentState) -> AgentState:
    """
    Execute lead capture if all three fields are present and
    the LLM has signalled trigger_lead_capture = true.
    Guard against double-capture with lead_captured flag.
    """
    if not state.get("trigger_lead_capture") or state.get("lead_captured"):
        return state

    lead = state["lead_info"]
    if all(k in lead for k in ("name", "email", "platform")):
        result = execute_tool(
            "mock_lead_capture",
            name=lead["name"],
            email=lead["email"],
            platform=lead["platform"],
        )
        return {**state, "lead_captured": True}

    return state


def history_node(state: AgentState) -> AgentState:
    """Append the current turn to conversation history."""
    new_messages = state["messages"] + [
        HumanMessage(content=state["user_input"]),
        AIMessage(content=state["agent_reply"]),
    ]
    return {**state, "messages": new_messages}


#graph assembly
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("llm", llm_node)
    graph.add_node("update_lead", update_lead_info_node)
    graph.add_node("tool_call", tool_node)
    graph.add_node("update_history", history_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "llm")
    graph.add_edge("llm", "update_lead")
    graph.add_edge("update_lead", "tool_call")
    graph.add_edge("tool_call", "update_history")
    graph.add_edge("update_history", END)

    return graph.compile()


#public interface
def get_initial_state() -> AgentState:
    return AgentState(
        messages=[],
        user_input="",
        rag_context="",
        intent="",
        agent_reply="",
        lead_field_collected=None,
        trigger_lead_capture=False,
        lead_info={},
        lead_captured=False,
    )


def run_turn(graph, state: AgentState, user_input: str) -> tuple[AgentState, str]:
    """
    Process one conversational turn.
    Returns (new_state, agent_reply_string).
    """
    state = {**state, "user_input": user_input}
    new_state = graph.invoke(state)
    return new_state, new_state["agent_reply"]