# Orchestrators

Orchestrators are a set of configured Operators and a resource manager. They provide a single entry point for common interactions with Operators

## `__init__`

- store_messages (bool): Whether to store Operator messages. Only works when the package `concrete-db` is installed.

## `add_operator`

- operator (Operator): The operator to add to the Orchestrator

- title (str): The title of the operator to be used to identify it in the orchestrator

## `process_new_project`

Creates and processes a new software project.

- starting_prompt (str): The starting prompt for the project
- project_id (uuid): Optional project ID for database integration.
- exec (str): The title of the operator to use as the 'executive'. Must be of type `operators.Executive`
- dev (str): The title of the operator to use as the 'developer' Must of type `operators.Developer`

Returns an AsyncGenerator of the project's messages.

---

Last Updated: 2024-12-04 09:21:32 UTC

Lines Changed: +5, -3
