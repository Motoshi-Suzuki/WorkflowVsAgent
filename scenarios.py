SCENARIOS: dict[str, dict] = {
    "simple": {
        "inquiry": "Hi, where's my order 1001? When will it arrive?",
        "description": "Single intent: shipping status lookup (parity case — workflow should match agent)",
    },
    "compound": {
        "inquiry": (
            "Can you change the delivery on order 1002 to tomorrow? "
            "If that's not possible, just cancel it and refund me."
        ),
        "description": (
            "Compound conditional: address change → fallback to cancel+refund. "
            "The workflow handles the first intent and stops; the agent follows the conditional."
        ),
    },
    "novel": {
        "inquiry": (
            "Your driver left my parcel out in the rain and the box is soaked. "
            "What are you going to do about it?"
        ),
        "description": (
            "Novel intent: damaged delivery with no matching workflow template. "
            "The agent reasons from policy and escalates; the workflow gives a generic reply."
        ),
    },
}
