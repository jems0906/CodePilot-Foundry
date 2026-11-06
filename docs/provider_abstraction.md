# Runbook: Add an LLM Provider

Providers implement `AgentProvider` in `backend/app/providers/base.py`: `generate_plan(task)`, `propose_code_change(task, plan, files)`, and `self_review(diff, test_result)`.

1. Add a provider module implementing all three methods. Return a complete proposed file body; never write files, execute tools, access the database, or select a command.
2. Validate every model response against a strict structured schema. Treat model output as untrusted even when it passes schema validation.
3. Add a provider branch in `get_provider` using a documented environment value. Never infer provider selection from source files or task content.
4. Read credentials only in the provider process and never pass them to the sandbox or include them in prompts, events, diffs, and error messages.
5. Keep the provider independent from persistence. Provider choice must not require a schema migration.
6. Add deterministic unit tests with mocked SDK responses, including malformed output and provider failure. Preserve the mock provider for offline development and CI.
7. Run the backend suite and verify the full task-to-review flow with the mock provider. Keep network-dependent tests opt-in.
8. Document package installation, environment variables, model selection, data handling, and failure behavior.

The optional OpenAI provider uses Structured Outputs with JSON Schema for plans, one-file proposals, and self-review. The mock provider remains the default.
