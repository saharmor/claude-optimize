"""
Customer Support Ticket Classifier & Responder

A sample application that classifies incoming support tickets by category and priority,
then drafts a response. This app deliberately contains common anti-patterns that the
Claude Optimize is designed to detect and fix.

Anti-patterns included:
1. Prompt Engineering: Vague system prompt, no XML tags, no examples, no output contract
2. Prompt Caching: Large system prompt sent fresh on every API call without caching
3. Batching: Processes tickets one-by-one in a loop instead of using Message Batches
4. Tool Use: All 8 tools passed to every call even when only classification is needed
5. Structured Outputs: Regex/json.loads parsing with retries instead of native structured outputs
"""

import json
import os
import re
import time

from anthropic import Anthropic

client = Anthropic()

# ---------------------------------------------------------------------------
# Anti-pattern #1 (Prompt Engineering): Vague, unstructured system prompt
# Anti-pattern #2 (Prompt Caching): This 2000+ token prompt is sent fresh every call
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful customer support assistant for ShopFlow, an e-commerce platform.

Our company ShopFlow was founded in 2019 and we sell a wide variety of products including electronics, clothing, home goods, and office supplies. We have over 50,000 products in our catalog and serve customers in 15 countries. Our headquarters is in San Francisco and we have warehouses in the US, EU, and Asia.

Here are our company policies that you must follow:

Return Policy: Customers can return most items within 30 days of delivery for a full refund. Items must be in original condition with tags attached. Electronics have a 15-day return window. Personalized or custom items cannot be returned. Sale items can only be exchanged, not refunded. Return shipping is free for defective items; otherwise, the customer pays return shipping. Refunds are processed within 5-7 business days after we receive the returned item.

Shipping Policy: Standard shipping is 5-7 business days. Express shipping is 2-3 business days. Overnight shipping is available for orders placed before 2pm EST. Free shipping on orders over $50. International shipping takes 7-14 business days. We ship via UPS, FedEx, and USPS. Tracking numbers are provided within 24 hours of shipment. If a package is lost, we will reship or refund after a 7-day investigation period.

Discount Policy: We offer 10% off for first-time customers. Bulk orders of 100+ units get 15% off. Corporate accounts get custom pricing. Coupon codes cannot be combined. Price matching is available within 7 days of purchase if the price drops. Student discounts of 5% are available with valid .edu email.

Escalation Policy: Escalate to a manager if the customer mentions legal action, requests to speak to a manager, has been waiting more than 48 hours for a resolution, or if the issue involves a charge over $500. Be empathetic and professional at all times. Never argue with the customer. If unsure about a policy, escalate rather than guess.

Tone Guidelines: Be friendly but professional. Use the customer's name when available. Acknowledge their frustration before offering solutions. Keep responses concise but thorough. Avoid jargon. Don't use exclamation marks excessively. Sign off with your name (Alex) and offer further assistance.

Privacy Policy: Never share customer data with other customers. Verify identity before sharing account details. Don't include full credit card numbers in responses. Refer PII-related requests to our privacy team at privacy@shopflow.com.

SLA Commitments: First response within 4 hours during business hours (9am-6pm EST). Resolution within 24 hours for urgent issues. Resolution within 72 hours for non-urgent issues. Weekend support is available but with extended response times.

You should categorize tickets and respond to them. Try to be helpful and follow the policies above. Return your response as JSON with the fields category, priority, and suggested_response."""


# ---------------------------------------------------------------------------
# Anti-pattern #4 (Tool Use): All 8 tools defined and sent on every request
# Even classification-only tasks get all tools
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    {
        "name": "lookup_customer",
        "description": "Look up a customer's account information including their order history, account status, subscription details, loyalty points balance, and communication preferences. This tool searches by email address and returns comprehensive customer profile data from our CRM system. Use this whenever you need to verify a customer's identity or understand their history with ShopFlow.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The customer's email address to look up in our system"
                }
            },
            "required": ["email"]
        }
    },
    {
        "name": "check_order_status",
        "description": "Check the current status of a specific order by its order ID. Returns detailed information including order items, quantities, prices, shipping method, tracking number, estimated delivery date, current fulfillment status (pending, processing, shipped, delivered, returned), and any notes from the warehouse team. Also returns the payment status and method used.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID (format: #XXXXX)"
                }
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "search_knowledge_base",
        "description": "Search our internal knowledge base for relevant articles, FAQs, troubleshooting guides, and policy documents. The knowledge base contains over 500 articles covering common issues, product specifications, setup guides, and policy explanations. Returns the top 5 most relevant articles with their titles, summaries, and full content. Use this to find accurate information before responding to customer queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant knowledge base articles"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "escalate_ticket",
        "description": "Escalate a support ticket to a human manager or specialized team. This marks the ticket as escalated in our system, notifies the appropriate team via Slack and email, and sets an SLA timer for manager response. Use this when the issue requires human judgment, involves potential legal matters, or when the customer explicitly requests to speak with a manager. Include a detailed summary so the manager has full context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "The ticket ID to escalate"},
                "reason": {"type": "string", "description": "Detailed reason for escalation"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]}
            },
            "required": ["ticket_id", "reason", "priority"]
        }
    },
    {
        "name": "apply_discount",
        "description": "Apply a discount code or special pricing to a customer's account or specific order. This tool can apply percentage discounts, fixed amount discounts, free shipping, or custom pricing. All discounts are logged for audit purposes and the customer receives an email confirmation. Manager approval is automatically requested for discounts over 25%. Use this when a customer is eligible for a promotion or when offering a goodwill discount.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_email": {"type": "string"},
                "discount_type": {"type": "string", "enum": ["percentage", "fixed", "free_shipping"]},
                "discount_value": {"type": "number"},
                "reason": {"type": "string"}
            },
            "required": ["customer_email", "discount_type", "discount_value", "reason"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an email to a customer or internal team member. Supports HTML formatting, attachments (by reference ID), and CC/BCC recipients. All sent emails are logged in the ticket history. Use this to send order confirmations, shipping updates, resolution summaries, or any other communication. The email is sent from support@shopflow.com unless otherwise specified.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string"},
                "body": {"type": "string", "description": "Email body (supports HTML)"},
                "cc": {"type": "array", "items": {"type": "string"}, "description": "CC recipients"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "log_interaction",
        "description": "Log a customer interaction in our CRM system for record-keeping and analytics. Every customer touchpoint should be logged including the channel (email, chat, phone), a summary of the interaction, the resolution status, and any follow-up actions needed. This data feeds into our customer satisfaction analytics dashboard and is used for quality assurance reviews.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "channel": {"type": "string", "enum": ["email", "chat", "phone"]},
                "summary": {"type": "string"},
                "resolution_status": {"type": "string", "enum": ["resolved", "pending", "escalated"]}
            },
            "required": ["ticket_id", "channel", "summary", "resolution_status"]
        }
    },
    {
        "name": "update_crm",
        "description": "Update a customer's CRM record with new information such as updated contact details, communication preferences, account notes, or tags. This tool modifies the customer's profile in our central CRM system. Changes are versioned and auditable. Use this to keep customer records accurate and up-to-date based on information gathered during support interactions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_email": {"type": "string"},
                "field": {"type": "string", "description": "The CRM field to update"},
                "value": {"type": "string", "description": "The new value"}
            },
            "required": ["customer_email", "field", "value"]
        }
    }
]


def classify_ticket(ticket: dict) -> dict:
    """
    Classify a single support ticket and generate a response.

    Anti-pattern #1: Vague prompt with no XML tags, no examples, no output contract
    Anti-pattern #2: Full system prompt sent without caching
    Anti-pattern #4: All 8 tools passed even though classification doesn't need most of them
    Anti-pattern #5: Asks for JSON in prose, then parses with retries
    """
    user_message = f"""Please classify this support ticket and draft a response.

Ticket ID: {ticket['id']}
Subject: {ticket['subject']}
Message: {ticket['body']}
Customer Email: {ticket['customer_email']}
Created: {ticket['created_at']}

Remember to return a JSON with category, priority, and suggested_response."""

    # Anti-pattern #5 (Structured Outputs): Retries with json.loads instead of using
    # native structured outputs or tool_use for guaranteed JSON
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=ALL_TOOLS,  # All 8 tools sent even for classification
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            # Extract text from response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Anti-pattern #5: Manual JSON extraction with regex fallback
            result = None
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to find JSON in the response
                json_match = re.search(r'\{[^{}]*"category"[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())

            if result and "category" in result:
                return result

            print(f"Attempt {attempt + 1}: Could not parse response, retrying...")

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

    return {
        "category": "unknown",
        "priority": "medium",
        "suggested_response": "We're looking into your request and will get back to you shortly."
    }


def process_ticket_backlog(tickets: list[dict]) -> list[dict]:
    """
    Process a backlog of support tickets.

    Anti-pattern #3 (Batching): Processes tickets sequentially in a for-loop.
    Each ticket gets its own API call, even though they're independent.
    The Message Batches API would give 50% cost savings here.
    """
    results = []
    for i, ticket in enumerate(tickets):
        print(f"Processing ticket {i + 1}/{len(tickets)}: {ticket['id']}")
        result = classify_ticket(ticket)
        result["ticket_id"] = ticket["id"]
        results.append(result)
        print(f"  -> Category: {result.get('category', 'unknown')}, "
              f"Priority: {result.get('priority', 'unknown')}")

    return results


def generate_daily_summary(results: list[dict]) -> str:
    """Generate a summary of the day's ticket processing."""
    categories = {}
    priorities = {}
    for r in results:
        cat = r.get("category", "unknown")
        pri = r.get("priority", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        priorities[pri] = priorities.get(pri, 0) + 1

    summary = "=== Daily Ticket Summary ===\n"
    summary += f"Total tickets processed: {len(results)}\n\n"
    summary += "By Category:\n"
    for cat, count in sorted(categories.items()):
        summary += f"  {cat}: {count}\n"
    summary += "\nBy Priority:\n"
    for pri, count in sorted(priorities.items()):
        summary += f"  {pri}: {count}\n"

    return summary


def main():
    # Load sample tickets
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tickets_path = os.path.join(script_dir, "sample_tickets.json")

    with open(tickets_path) as f:
        tickets = json.load(f)

    print(f"Loaded {len(tickets)} tickets\n")

    # Process all tickets (anti-pattern #3: sequential processing)
    results = process_ticket_backlog(tickets)

    # Generate and print summary
    summary = generate_daily_summary(results)
    print(f"\n{summary}")

    # Save results
    output_path = os.path.join(script_dir, "results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
