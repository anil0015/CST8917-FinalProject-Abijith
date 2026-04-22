# =============================================================================
# ExpenseFlow — Expense Validation Azure Function
# CST8917 Final Project — Logic Apps, Service Bus & Azure Functions
# =============================================================================
# This Azure Function is called by the Logic App to validate expense requests.
# It checks required fields, validates category and amount values, and returns
# a result that the Logic App can use for branching.
# =============================================================================

import azure.functions as func
import json
import logging

# =============================================================================
# CREATE THE FUNCTION APP
# =============================================================================
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# =============================================================================
# VALID EXPENSE CATEGORIES
# =============================================================================
# These are the only categories accepted by the final project requirements.

VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_text(value):
    """Convert a value to a trimmed string."""
    return str(value).strip() if value is not None else ""


# =============================================================================
# VALIDATE EXPENSE FUNCTION
# =============================================================================
# Decision logic:
#   1. Parse the incoming JSON body
#   2. Check required fields
#   3. Validate category
#   4. Validate amount
#   5. Validate email fields
#   6. Return a validation result for the Logic App
#
# Logic App usage:
#   - If is_valid = false -> validation error branch
#   - If amount < 100 -> auto-approve branch
#   - If amount >= 100 -> manager approval branch

@app.function_name(name="validate-expense")
@app.route(route="", methods=["POST"])
def validate_expense(req: func.HttpRequest) -> func.HttpResponse:
    """
    Validate an expense request.

    Expected JSON body:
    {
        "expenseId": "EXP-1001",
        "employee_name": "Nina Patel",
        "employee_email": "nina.patel@contoso-demo.com",
        "amount": 64,
        "category": "supplies",
        "description": "Office stationery for project meeting",
        "manager_email": "oliver.grant@contoso-demo.com"
    }
    """
    logging.info("validate-expense function triggered")

    try:
        expense = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({
                "is_valid": False,
                "status": "validation_error",
                "message": "Invalid JSON body"
            }),
            mimetype="application/json",
            status_code=400
        )

    # -------------------------------------------------------------------------
    # Validate required fields
    # -------------------------------------------------------------------------
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
        result = {
            "expenseId": expense.get("expenseId", "N/A"),
            "employee_name": normalize_text(expense.get("employee_name")),
            "employee_email": normalize_text(expense.get("employee_email")),
            "amount": expense.get("amount"),
            "category": normalize_text(expense.get("category")).lower(),
            "description": normalize_text(expense.get("description")),
            "manager_email": normalize_text(expense.get("manager_email")),
            "is_valid": False,
            "status": "validation_error",
            "message": f"Missing required fields: {', '.join(missing_fields)}"
        }

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    # -------------------------------------------------------------------------
    # Validate category
    # -------------------------------------------------------------------------
    category = normalize_text(expense.get("category")).lower()

    if category not in VALID_CATEGORIES:
        result = {
            "expenseId": expense.get("expenseId", "N/A"),
            "employee_name": normalize_text(expense.get("employee_name")),
            "employee_email": normalize_text(expense.get("employee_email")),
            "amount": expense.get("amount"),
            "category": category,
            "description": normalize_text(expense.get("description")),
            "manager_email": normalize_text(expense.get("manager_email")),
            "is_valid": False,
            "status": "validation_error",
            "message": f"Invalid category: {category}"
        }

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    # -------------------------------------------------------------------------
    # Validate amount
    # -------------------------------------------------------------------------
    try:
        amount = float(expense.get("amount"))
        if amount < 0:
            result = {
                "expenseId": expense.get("expenseId", "N/A"),
                "employee_name": normalize_text(expense.get("employee_name")),
                "employee_email": normalize_text(expense.get("employee_email")),
                "amount": expense.get("amount"),
                "category": category,
                "description": normalize_text(expense.get("description")),
                "manager_email": normalize_text(expense.get("manager_email")),
                "is_valid": False,
                "status": "validation_error",
                "message": "Amount must be zero or greater"
            }

            return func.HttpResponse(
                json.dumps(result),
                mimetype="application/json",
                status_code=200
            )

    except (TypeError, ValueError):
        result = {
            "expenseId": expense.get("expenseId", "N/A"),
            "employee_name": normalize_text(expense.get("employee_name")),
            "employee_email": normalize_text(expense.get("employee_email")),
            "amount": expense.get("amount"),
            "category": category,
            "description": normalize_text(expense.get("description")),
            "manager_email": normalize_text(expense.get("manager_email")),
            "is_valid": False,
            "status": "validation_error",
            "message": "Amount must be a valid number"
        }

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    # -------------------------------------------------------------------------
    # Validate email fields
    # -------------------------------------------------------------------------
    employee_email = normalize_text(expense.get("employee_email"))
    manager_email = normalize_text(expense.get("manager_email"))

    if "@" not in employee_email:
        result = {
            "expenseId": expense.get("expenseId", "N/A"),
            "employee_name": normalize_text(expense.get("employee_name")),
            "employee_email": employee_email,
            "amount": amount,
            "category": category,
            "description": normalize_text(expense.get("description")),
            "manager_email": manager_email,
            "is_valid": False,
            "status": "validation_error",
            "message": "Employee email is invalid"
        }

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    if "@" not in manager_email:
        result = {
            "expenseId": expense.get("expenseId", "N/A"),
            "employee_name": normalize_text(expense.get("employee_name")),
            "employee_email": employee_email,
            "amount": amount,
            "category": category,
            "description": normalize_text(expense.get("description")),
            "manager_email": manager_email,
            "is_valid": False,
            "status": "validation_error",
            "message": "Manager email is invalid"
        }

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    # -------------------------------------------------------------------------
    # Build a response for the Logic App
    # -------------------------------------------------------------------------
    # Expenses under $100 can be auto-approved later in the Logic App.
    # Expenses of $100 or more should move to the manager approval path.

    if amount < 100:
        decision_hint = "approved"
        message = "Expense is valid and qualifies for automatic approval"
    else:
        decision_hint = "manager_review"
        message = "Expense is valid and requires manager approval"

    result = {
        "expenseId": expense.get("expenseId", "N/A"),
        "employee_name": normalize_text(expense.get("employee_name")),
        "employee_email": employee_email,
        "amount": amount,
        "category": category,
        "description": normalize_text(expense.get("description")),
        "manager_email": manager_email,
        "is_valid": True,
        "status": "validated",
        "decision_hint": decision_hint,
        "message": message
    }

    logging.info(
        "Expense %s validated successfully | amount=%s | decision_hint=%s",
        result["expenseId"],
        result["amount"],
        result["decision_hint"]
    )

    return func.HttpResponse(
        json.dumps(result),
        mimetype="application/json",
        status_code=200
    )


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.function_name(name="health")
@app.route(route="", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "Expense Validation Function App",
            "valid_categories": sorted(list(VALID_CATEGORIES))
        }),
        mimetype="application/json",
        status_code=200
    )