# AI Assistant Instructions

These instructions define the standard workflow that the AI must follow when modifying this project.

## Workflow Rules

When writing new code or modifying existing code, you **MUST** always perform the following steps:

1.  **Lint & Format**: Ensure code is clean and formatted.
    *   Run `uv run ruff check .` and `uv run ruff format .`.
2.  **Test**: Write any new tests that are needed and ensure **ALL** tests pass.
    *   Run `uv run pytest` (and `uv run pytest --cov=src` if appropriate) to verify.
2.  **Document**: Update the project documentation to reflect changes.
    *   Update `docs/` files if features change.
    *   Update `README.md` if high-level info changes.
3.  **Summarize**: Update `ai/session_summary.md` with a log of your actions.
    *   Append a new entry describing what was done, why, and the outcome.

## Directory Structure
-   `ai/`: Contains AI context, summaries, and these instructions.
