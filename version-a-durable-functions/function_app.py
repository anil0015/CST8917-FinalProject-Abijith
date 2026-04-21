import json
from datetime import timedelta

import azure.functions as func
import azure.durable_functions as df

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}


@app.route(route="expense/start", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_expense(req: func.HttpRequest, client):
    try:
        data = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    instance_id = await client.start_new("expense_orchestrator", client_input=data)
    return client.create_check_status_response(req, instance_id)


@app.orchestration_trigger(context_name="context")
def expense_orchestrator(context: df.DurableOrchestrationContext):
    expense = context.get_input()

    validation = yield context.call_activity("validate_expense", expense)

    if not validation["is_valid"]:
        result = {
            "status": "validation_error",
            "message": validation["message"],
            "expense": expense
        }
        yield context.call_activity("send_notification", result)
        return result

    amount = float(expense["amount"])

    if amount < 100:
        result = {
            "status": "approved",
            "escalated": False,
            "message": "Auto-approved because amount is under $100.",
            "expense": expense
        }
        yield context.call_activity("send_notification", result)
        return result

    timeout_at = context.current_utc_datetime + timedelta(minutes=1)

    approval_task = context.wait_for_external_event("ManagerDecision")
    timeout_task = context.create_timer(timeout_at)

    winner = yield context.task_any([approval_task, timeout_task])

    if winner == approval_task:
        decision = approval_task.result
        result = {
            "status": decision["decision"],
            "escalated": False,
            "message": f"Manager {decision['decision']} the expense.",
            "expense": expense
        }
    else:
        result = {
            "status": "approved",
            "escalated": True,
            "message": "No manager response before timeout. Auto-approved and escalated.",
            "expense": expense
        }

    yield context.call_activity("send_notification", result)
    return result


@app.activity_trigger(input_name="expense")
def validate_expense(expense: dict):
    required_fields = [
        "employee_name",
        "employee_email",
        "amount",
        "category",
        "description",
        "manager_email"
    ]

    for field in required_fields:
        if field not in expense or str(expense[field]).strip() == "":
            return {"is_valid": False, "message": f"Missing required field: {field}"}

    if str(expense["category"]).lower() not in VALID_CATEGORIES:
        return {"is_valid": False, "message": "Invalid category"}

    try:
        float(expense["amount"])
    except ValueError:
        return {"is_valid": False, "message": "Amount must be numeric"}

    return {"is_valid": True, "message": "Valid expense"}


@app.activity_trigger(input_name="result")
def send_notification(result: dict):
    print("EMAIL TO:", result["expense"].get("employee_email"))
    print("SUBJECT: Expense Request Outcome")
    print("BODY:", json.dumps(result, indent=2))
    return "Notification processed"


@app.route(route="expense/approve", methods=["POST"])
@app.durable_client_input(client_name="client")
async def manager_approval(req: func.HttpRequest, client):
    try:
        data = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    instance_id = data.get("instance_id")
    decision = data.get("decision")

    if not instance_id or decision not in ["approved", "rejected"]:
        return func.HttpResponse(
            "Provide instance_id and decision=approved|rejected",
            status_code=400
        )

    await client.raise_event(instance_id, "ManagerDecision", {"decision": decision})
    return func.HttpResponse(f"Decision '{decision}' sent to instance {instance_id}")