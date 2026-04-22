"""
Terminal chat loop — run this to test the agent locally before building any UI.

Usage:
    python main.py

Type 'quit' or 'exit' to stop.
Type 'state' to print the current agent state (debug mode).
"""
from dotenv import load_dotenv
load_dotenv()  # reads .env into environment automatically

from agent import build_graph, get_initial_state, run_turn


WELCOME = """
╔══════════════════════════════════════════════════════╗
║        AutoStream AI Agent — Terminal Demo           ║
║   Type 'quit' to exit  |  'state' to debug           ║
╚══════════════════════════════════════════════════════╝
"""


def format_intent_badge(intent: str) -> str:
    badges = {
        "GREETING": "👋 GREETING",
        "INQUIRY": "🔍 INQUIRY",
        "HIGH_INTENT": "🔥 HIGH_INTENT",
    }
    return badges.get(intent, intent)


def main():
    print(WELCOME)
    graph = build_graph()
    state = get_initial_state()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        if user_input.lower() == "state":
            import json
            # Print state without messages (too verbose)
            debug = {k: v for k, v in state.items() if k != "messages"}
            debug["message_count"] = len(state.get("messages", []))
            print("\n[DEBUG STATE]")
            print(json.dumps(debug, indent=2, default=str))
            print()
            continue

        state, reply = run_turn(graph, state, user_input)

        print(f"\n[{format_intent_badge(state['intent'])}]")
        print(f"Maya: {reply}\n")

        # Show lead capture confirmation inline
        if state.get("lead_captured") and state.get("lead_info"):
            li = state["lead_info"]
            print(f"  Lead saved → {li.get('name')} | {li.get('email')} | {li.get('platform')}\n")


if __name__ == "__main__":
    main()