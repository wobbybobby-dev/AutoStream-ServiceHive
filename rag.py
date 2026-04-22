"""
RAG (Retrieval-Augmented Generation) module for AutoStream agent.

For this small, structured knowledge base we use keyword-based retrieval
rather than vector embeddings — it's faster, has zero dependencies, and
is perfectly accurate for a known set of topics.

If you want to upgrade to semantic search later, swap retrieve_context()
to use sentence-transformers + cosine similarity on the same chunks.
"""

import json
import re
from pathlib import Path

KB_PATH = Path(__file__).parent / "local_database.json"


def load_knowledge_base() -> dict:    #opens database and loads it in a dictionary
    with open(KB_PATH, "r") as f:
        return json.load(f)


def _flatten_to_chunks(kb: dict) -> list[dict]:    
    chunks = []

    #Company overview
    chunks.append({
        "id": "company_overview",
        "keywords": ["autostream", "what is", "about", "company", "product", "overview"],
        "text": (
            f"{kb['company']['name']}: {kb['company']['description']} "
            f"Tagline: \"{kb['company']['tagline']}\""
        )
    })

    #Basic plan
    bp = kb["plans"]["basic"]
    chunks.append({
        "id": "plan_basic",
        "keywords": ["basic", "plan", "price", "pricing", "cost", "cheap", "starter", "29", "720"],
        "text": (
            f"Basic Plan — ${bp['price_monthly']}/month. "
            f"Features: {', '.join(bp['features'])}. "
            f"Best for: {bp['best_for']}."
        )
    })

    #Pro plan
    pp = kb["plans"]["pro"]
    chunks.append({
        "id": "plan_pro",
        "keywords": ["pro", "plan", "price", "pricing", "cost", "unlimited", "4k", "captions", "79", "professional"],
        "text": (
            f"Pro Plan — ${pp['price_monthly']}/month. "
            f"Features: {', '.join(pp['features'])}. "
            f"Best for: {pp['best_for']}."
        )
    })

    #Pricing comparison (both plans together)
    chunks.append({
        "id": "pricing_comparison",
        "keywords": ["pricing", "plans", "compare", "difference", "vs", "which plan", "options"],
        "text": (
            f"AutoStream has two plans. "
            f"Basic: ${bp['price_monthly']}/month — {bp['features'][0]}, {bp['features'][1]}. "
            f"Pro: ${pp['price_monthly']}/month — {pp['features'][0]}, {pp['features'][1]}, {pp['features'][2]}, plus 24/7 support."
        )
    })

    #Policies
    pol = kb["policies"]
    chunks.append({
        "id": "policy_refund",
        "keywords": ["refund", "money back", "cancel", "return", "policy", "days"],
        "text": f"Refund policy: {pol['refunds']}"
    })
    chunks.append({
        "id": "policy_support",
        "keywords": ["support", "help", "contact", "chat", "24/7", "customer service"],
        "text": f"Support policy: {pol['support']}"
    })
    chunks.append({
        "id": "policy_trial",
        "keywords": ["trial", "free", "try", "test", "no credit card", "7 day"],
        "text": f"Free trial: {pol['free_trial']}"
    })
    chunks.append({
        "id": "policy_cancel",
        "keywords": ["cancel", "cancellation", "stop", "end subscription"],
        "text": f"Cancellation: {pol['cancellation']}"
    })
    chunks.append({
        "id": "policy_billing",
        "keywords": ["billing", "annual", "yearly", "monthly", "discount", "payment"],
        "text": f"Billing: {pol['billing']}"
    })

    #FAQs
    for i, faq in enumerate(kb["faqs"]):
        words = re.findall(r'\b\w{4,}\b', faq["question"].lower())        #extract keywords from the question
        chunks.append({
            "id": f"faq_{i}",
            "keywords": words,
            "text": f"Q: {faq['question']} A: {faq['answer']}"
        })

    return chunks


def retrieve_context(query: str, top_k: int = 3) -> str:
    """
    Given a user query, returns the most relevant knowledge base chunks(top 3)
    as a single formatted string to inject into the LLM prompt.

    Scoring: count how many of a chunk's keywords appear in the query.
    Ties are broken by order (more specific chunks ranked first).
    """
    kb = load_knowledge_base()
    chunks = _flatten_to_chunks(kb)

    query_lower = query.lower()
    query_words = set(re.findall(r'\b\w+\b', query_lower))

    #creating list containing chunks and their scores
    scored = []
    for chunk in chunks:
        score = sum(1 for kw in chunk["keywords"] if kw in query_lower or kw in query_words)
        scored.append((score, chunk))

    #Sort by score descending; always include at least the pricing comparison chunk
    scored.sort(key=lambda x: x[0], reverse=True)

    #always include pricing if score > 0 on top chunks, else include top_k anyway
    selected = [c for _, c in scored[:top_k] if _ > 0]
    if not selected:
        selected = [c for _, c in scored[:2]]  #fallback: top 2 regardless

    #deduplicate by id
    seen = set()
    unique = []
    for c in selected:
        if c["id"] not in seen:
            seen.add(c["id"])
            unique.append(c)

    context_text = "\n\n".join(f"[{c['id']}] {c['text']}" for c in unique)
    return context_text


if __name__ == "__main__":
    #quick test
    queries = [
        "What's the difference between Basic and Pro?",
        "Do you offer refunds?",
        "I want to try the Pro plan",
        "How much does it cost?",
    ]
    for q in queries:
        print(f"\nQuery: {q}")
        print("Context:", retrieve_context(q))
        print("-" * 60)