## Version A - Durable Functions Summary

Version A was implemented using Azure Durable Functions with the Python v2 programming model. The workflow starts through an HTTP endpoint, validates the request, auto-approves expenses under $100, and waits for a manager decision for expenses of $100 or more.

A durable timer was used to handle the timeout scenario. If no manager response is received in time, the request is automatically approved and flagged as escalated. I also used separate activity functions for validation, auditing, and notification. After fixing some local setup and binding issues, all required test scenarios worked successfully.