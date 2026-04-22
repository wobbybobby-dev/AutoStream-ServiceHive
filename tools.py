"""
Tool definitions for the AutoStream agent.
Currently contains the mock lead capture function.
Add more tools here as the agent grows (e.g., calendar booking, demo scheduling).
"""

import json
from datetime import datetime


def mock_lead_capture(name: str, email: str, platform: str) -> dict:
    """
    Mock API call that simulates saving a lead to a CRM.
    """
    
    if not all([name, email, platform]):
        return {"success": False, "error": "Missing required fields"}
    
    if "@" not in email:
        return {"success": False, "error": "Invalid email format"}

    #Mock the CRM save
    lead_data = {
        "name": name,
        "email": email,
        "platform": platform,
        "source": "social_chat",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "lead_id": f"LEAD-{hash(email) % 100000:05d}",  # fake ID
    }

    #In a real system, this would be an API call
    print(f"\n{'='*50}")
    print(f"LEAD CAPTURED SUCCESSFULLY")
    print(f"{'='*50}")
    print(f"  Name     : {lead_data['name']}")
    print(f"  Email    : {lead_data['email']}")
    print(f"  Platform : {lead_data['platform']}")
    print(f"  Lead ID  : {lead_data['lead_id']}")
    print(f"  Time     : {lead_data['timestamp']}")
    print(f"{'='*50}\n")

    return {"success": True, "lead_id": lead_data["lead_id"], "data": lead_data}


TOOLS = {
    "mock_lead_capture": mock_lead_capture,
}


def execute_tool(tool_name: str, **kwargs) -> dict:
    if tool_name not in TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
    return TOOLS[tool_name](**kwargs)