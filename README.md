# Final Assignment 
## Name: Abijith Anil  
## Student Number: 041194855  
## Course: CST8917 - Serverless Applications  

## Version A Summary

Version A was implemented using Azure Durable Functions with the Python v2 programming model. This version focuses on a code-first workflow where the expense request is received through an HTTP endpoint and processed through an orchestrator and activity functions.

The workflow validates the request first, then applies the business rules. If the expense amount is under $100, it is automatically approved. If the amount is $100 or more, the orchestrator waits for a manager decision. If the manager approves, the expense is approved. If the manager rejects, the expense is rejected. If no decision is received before the timeout period, the expense is marked as escalated. Validation errors are also handled for missing fields or invalid categories.

One important design choice in this version was to keep the business logic inside the Durable Functions workflow itself. The orchestrator controls the flow, while the activity functions handle validation, audit logging, and notifications. This made the process easier to follow because the workflow was centralized in one code-based implementation.

A major strength of this version is that it is easier to test locally and easier to debug because the logic is all in one place. At the same time, the setup still required careful work, especially when dealing with local Azure Functions runtime issues and Durable Function bindings. Once those issues were fixed, the workflow behaved consistently and passed all required test cases.

## Version B Summary

Version B was implemented using Azure Logic Apps, Azure Service Bus, and an Azure Function for validation. This version follows a more distributed design where different services are responsible for different parts of the workflow.

In this version, an expense request is sent to a Service Bus queue. A Logic App reads the message, decodes it, parses the JSON, and then calls the Azure Function to validate the expense request. If the request is invalid, the workflow follows the validation error path. If the expense amount is under $100, it is automatically approved. If the amount is $100 or more, the workflow moves into the manager review path.

For the manager approval part, I used a simple simulated approach in the Logic App by checking the manager decision value included in the request. If the value is approved, the Logic App marks the request as approved. If it is rejected, the Logic App marks it as rejected. If no manager response is provided, the Logic App treats it as no response and marks the request as escalated. After that, the workflow sends an email to the employee and publishes the result to a Service Bus topic with filtered subscriptions for approved, rejected, and escalated results.

This version felt more like a real cloud workflow because it used queues, topic subscriptions, and separate services communicating with each other. It was more flexible than Version A, but also more difficult to configure. The main challenges were setting up the Service Bus connection correctly, making sure the Logic App conditions matched the expected fields, and testing the branches carefully to confirm that the correct email and topic message were produced.

## Comparison Analysis

The biggest difference between Version A and Version B is how each one handles orchestration. Version A uses Durable Functions, which means the workflow is written directly in code. The orchestration, timer handling, and branching logic are all managed from the Python application. Version B uses Logic Apps with Service Bus, so the workflow is built visually and spread across managed Azure services. Instead of having one code-driven orchestrator, the logic is represented as queue triggers, parse steps, conditions, email actions, and topic publishing steps.

From a development experience point of view, Version A was more straightforward once the local environment worked properly. I could open the code, understand the sequence of steps, and trace the logic from input to output more directly. It felt closer to a traditional programming task. Version B was easier to understand at a high level because the workflow is visible in the designer, but building it took more time because every condition, connector, and field mapping had to be configured carefully. A small mistake in a field name or connection could cause the whole Logic App path to behave unexpectedly. Because of that, Version A gave me more confidence in the logic itself, while Version B gave me a better picture of the workflow structure.

Testability was also different between the two approaches. Version A was easier to test locally because the functions could be run through HTTP requests using the REST client file. I could quickly try each required scenario and see the output. That made debugging faster. Version B was harder to test locally because it depended on Azure resources such as Service Bus, the deployed Azure Function, the Logic App, topic subscriptions, and the email connector. Testing Version B felt more like integration testing than simple local function testing. It still worked well, but it required more setup and more manual checking through the portal.

Error handling is another area where the two versions behaved differently. In Version A, I had more direct control over how validation errors, manager decisions, and timeout results were returned. The orchestrator decided the flow and built a clear result object. In Version B, error handling depended on the Logic App branches and service configuration. This made the flow flexible, but it also meant I had to think about whether the request failed during validation, connector setup, queue processing, or email delivery. Version B uses managed services that improve reliability, but it can be harder to isolate the exact source of an error when several Azure services are involved.

The human interaction pattern was where the biggest practical difference appeared. Durable Functions supports waiting for external input and combining that with a timer in a way that feels natural for approval workflows. That made Version A strong from a workflow logic perspective. In Version B, Logic Apps did not support that same pattern as naturally, so I had to use a simpler approach for manager review. I simulated the manager decision inside the request path and treated a missing decision as no response, which allowed me to still represent approved, rejected, and escalated outcomes. This worked for the project requirements, but it felt less elegant than the Durable Functions version.

Observability was mixed. Version A was easier to follow from a code and logs perspective because the workflow was contained within the function app. Version B was stronger visually because the Logic App run history showed exactly which steps succeeded, failed, or were skipped. For example, I could clearly see whether the request went into the validation error branch, the auto-approved branch, or the manager review branch. This made Version B useful for demonstrating the workflow during testing and screenshots. In that sense, Version B was easier to monitor visually, while Version A was easier to reason about from a developer perspective.

Cost also creates an important contrast between the two designs. For Version A, I mainly developed and tested locally, so the effective cost during development was minimal. If it were deployed to Azure, the cost would still likely be low at small scale because Azure Functions can be inexpensive for event-driven workloads. Version B uses more managed services such as Logic Apps, Service Bus, and connectors, so it has a more visible cloud cost. At around 100 expenses per day, the estimated monthly cost would still be relatively low and reasonable for a small business workflow. At around 10,000 expenses per day, the cost would increase much more noticeably because each request uses multiple service operations, including queue activity, Logic App actions, topic messages, and email-related processing. This means Version B provides a more realistic cloud architecture, but it also brings more infrastructure cost.

Overall, Version A felt stronger for workflow control, local testing, and handling approval logic in code. Version B felt stronger for realistic service integration, visual monitoring, and message-based cloud architecture. Version A is simpler and more direct. Version B is more distributed and closer to how a business system might be built in practice using Azure services. Both versions meet the same business requirements, but they do so in very different ways.

## Recommendation

If I had to choose one approach for production, I would recommend Version B with Logic Apps, Service Bus, and Azure Functions.

The main reason is that Version B behaves more like a real cloud system. Instead of keeping everything inside one application, it separates responsibilities across services. Service Bus handles the message flow, Logic Apps manages the orchestration, and the Azure Function performs validation. This makes the workflow easier to extend later if more steps are needed, such as logging, extra approval levels, dashboards, or integration with other systems.

Another reason is that Version B is easier to demonstrate and monitor through the Azure portal. The run history makes it clear which branch was taken and which actions completed successfully. For an approval workflow that may involve several stages, this visibility is useful.

That said, I would still choose Version A in situations where the workflow logic is more complex and I want stronger control in code, especially for human interaction patterns and timers. Durable Functions handled the approval flow more naturally from a developer point of view. Even so, because the final project asked for a more realistic cloud-based version, I think Version B is the better recommendation overall. It is more scalable, more service-oriented, and closer to how an actual enterprise workflow might be implemented.

## AI Disclosure

AI tools were used to help organize ideas, improve wording, and draft parts of the documentation and presentation materials. I reviewed and edited the output, adjusted it to match my own project, and made sure the final submission reflected my understanding of the work.
