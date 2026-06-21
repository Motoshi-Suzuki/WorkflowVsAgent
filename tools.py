import json
import pathlib

DATA = pathlib.Path(__file__).parent / "data"

TOOL_DEFINITIONS = [
    {
        "name": "get_order",
        "description": "Retrieve order details: items, status, order_date, customer_id, and total.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID, e.g. '1001'"}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_shipping_status",
        "description": (
            "Retrieve shipping status for an order: state "
            "(processing | dispatched | in_transit | delivered), "
            "dispatched_at, eta, and can_change_address."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID"}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_customer",
        "description": "Retrieve customer details: name, email, and tier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID, e.g. 'C1'"}
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "lookup_policy",
        "description": (
            "Look up store policy text for a specific topic. "
            "Valid topics: refund, address_change, cancellation, returns, damage."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": ["refund", "address_change", "cancellation", "returns", "damage"],
                    "description": "Policy topic",
                }
            },
            "required": ["topic"],
        },
    },
]


def get_order(order_id: str) -> dict:
    orders = json.loads((DATA / "orders.json").read_text())
    for o in orders:
        if str(o["id"]) == str(order_id):
            return o
    return {"error": f"Order {order_id!r} not found"}


def get_shipping_status(order_id: str) -> dict:
    records = json.loads((DATA / "shipping.json").read_text())
    for s in records:
        if str(s["order_id"]) == str(order_id):
            return s
    return {"error": f"No shipping record for order {order_id!r}"}


def get_customer(customer_id: str) -> dict:
    customers = json.loads((DATA / "customers.json").read_text())
    for c in customers:
        if c["id"] == customer_id:
            return c
    return {"error": f"Customer {customer_id!r} not found"}


def lookup_policy(topic: str) -> str:
    valid = {"refund", "address_change", "cancellation", "returns", "damage"}
    if topic not in valid:
        return f"Unknown topic '{topic}'. Valid topics: {', '.join(sorted(valid))}"

    text = (DATA / "policies.md").read_text()
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = line[3:].strip().lower()
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections.get(topic, f"No policy text found for '{topic}'.")


def execute_tool(name: str, tool_input: dict) -> str:
    fn = {
        "get_order": get_order,
        "get_shipping_status": get_shipping_status,
        "get_customer": get_customer,
        "lookup_policy": lookup_policy,
    }[name]
    result = fn(**tool_input)
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)
    return str(result)


def fmt_args(d: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in d.items())
