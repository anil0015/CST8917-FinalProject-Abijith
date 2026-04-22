import logging
from datetime import timedelta

import azure.durable_functions as df
import azure.functions as func

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}
APPROVAL_TIMEOUT_SECONDS = 120


def normalize_text(value):
    return str(value).strip() if value is not None else ""


def build_outcome(status, reason, expense, escalated=False):
    return {
        "final_status": status,
        "reason": reason,
        "escalated": escalated,
        "expense": expense
    }


@app.route(route="start-expense", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_expense(req: func.HttpRequest, client):
    try:
        expense = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    instance_id = await client.start_new("expense_orchestrator", None, expense)

    logging.info("Started expense workflow with instance ID: %s", instance_id)
    return client.create_check_status_response(req, instance_id)


@app.orchestration_trigger(context_name="context")
def expense_orchestrator(context: df.DurableOrchestrationContext):
    expense = context.get_input() or {}

    validation_result = yield context.call_activity("validate_expense", expense)

    if not validation_result["is_valid"]:
        result = build_outcome(
            status="validation_error",
            reason=validation_result["message"],
            expense=expense,
            escalated=False
        )
        yield context.call_activity("audit_expense_result", result)
        yield context.call_activity("send_notification", result)
        return result

    amount = float(expense["amount"])

    if amount < 100:
        result = build_outcome(
            status="approved",
            reason="Automatically approved because the amount is under $100",
            expense=expense,
            escalated=False
        )
        yield context.call_activity("audit_expense_result", result)
        yield context.call_activity("send_notification", result)
        return result

    deadline = context.current_utc_datetime + timedelta(seconds=APPROVAL_TIMEOUT_SECONDS)
    timeout_task = context.create_timer(deadline)
    approval_task = context.wait_for_external_event("ManagerDecision")

    yield context.task_any([approval_task, timeout_task])

    if approval_task.is_completed:
        if not timeout_task.is_completed:
            timeout_task.cancel()

        manager_decision = str(approval_task.result).strip().lower()

        if manager_decision == "approved":
            result = build_outcome(
                status="approved",
                reason="Manager approved the expense request",
                expense=expense,
                escalated=False
            )
        elif manager_decision == "rejected":
            result = build_outcome(
                status="rejected",
                reason="Manager rejected the expense request",
                expense=expense,
                escalated=False
            )
        else:
            result = build_outcome(
                status="validation_error",
                reason=f"Unsupported manager decision received: {manager_decision}",
                expense=expense,
                escalated=False
            )
    else:
        result = build_outcome(
            status="escalated",
            reason="No manager response before timeout, so the expense was auto-approved and escalated",
            expense=expense,
            escalated=True
        )

    yield context.call_activity("audit_expense_result", result)
    yield context.call_activity("send_notification", result)

    return result


@app.activity_trigger(input_name="expense")
def validate_expense(expense):
    required_fields = [
        "employee_name",
        "employee_email",
        "amount",
        "category",
        "description",
        "manager_email"
    ]

    missing_fields = [
        field for field in required_fields
        if normalize_text(expense.get(field)) == ""
    ]

    if missing_fields:
        return {
            "is_valid": False,
            "message": f"Missing required fields: {', '.join(missing_fields)}"
        }

    category = normalize_text(expense.get("category")).lower()
    if category not in VALID_CATEGORIES:
        return {
            "is_valid": False,
            "message": f"Invalid category: {category}"
        }

    try:
        amount = float(expense.get("amount"))
        if amount < 0:
            return {
                "is_valid": False,
                "message": "Amount must be zero or greater"
            }
    except (TypeError, ValueError):
        return {
            "is_valid": False,
            "message": "Amount must be a valid number"
        }

    employee_email = normalize_text(expense.get("employee_email"))
    manager_email = normalize_text(expense.get("manager_email"))

    if "@" not in employee_email:
        return {
            "is_valid": False,
            "message": "Employee email is invalid"
        }

    if "@" not in manager_email:
        return {
            "is_valid": False,
            "message": "Manager email is invalid"
        }

    return {
        "is_valid": True,
        "message": "Expense request passed validation"
    }


@app.activity_trigger(input_name="result")
def audit_expense_result(result):
    expense = result.get("expense", {})
    logging.info(
        "AUDIT | employee=%s | amount=%s | category=%s | final_status=%s | escalated=%s",
        expense.get("employee_name", "unknown"),
        expense.get("amount", "unknown"),
        expense.get("category", "unknown"),
        result.get("final_status", "unknown"),
        result.get("escalated", False)
    )
    return "Audit log recorded"


@app.activity_trigger(input_name="result")
def send_notification(result):
    expense = result.get("expense", {})
    logging.info(
        "NOTIFICATION | to=%s | status=%s | reason=%s",
        expense.get("employee_email", "unknown"),
        result.get("final_status"),
        result.get("reason")
    )
    return "Notification sent"


@app.route(route="manager-decision", methods=["POST"])
@app.durable_client_input(client_name="client")
async def manager_decision(req: func.HttpRequest, client):
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    instance_id = normalize_text(body.get("instance_id"))
    decision = normalize_text(body.get("decision")).lower()

    if not instance_id:
        return func.HttpResponse("instance_id is required", status_code=400)

    if decision not in {"approved", "rejected"}:
        return func.HttpResponse(
            "decision must be either 'approved' or 'rejected'",
            status_code=400
        )

    await client.raise_event(instance_id, "ManagerDecision", decision)

    logging.info("Manager decision '%s' sent to instance %s", decision, instance_id)
    return func.HttpResponse("Manager decision submitted successfully", status_code=200)