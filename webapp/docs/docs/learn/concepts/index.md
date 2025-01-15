# Key Concepts

**[Operators](operators.md)**  
An `Operator` represents an LLM-backed agent. Chat, command, duplicate, modify, coordinate, and deploy them with concrete.

**[Projects](projects.md)**  
A `Project` represents a unit of work executed on and returned to a user or another Operator.

**Orchestrators**  
`Orchestrator`s describe the way that operators interact with each other. It also encapsulates the orchestrators inside it with its own set of operators, tools, and clients.

**[Tools](tools.md)**  
`Tool`s enable an `Operator` to interact with the internet or real world.

**Clients**  
`Client`s are the internal interface to an API or other programmatic backend.

**agentserver**
`agentserver` are long-running processes providing an entrypoint for Operators and Tools to interact.

---

Last Updated: 2025-01-15 02:47:48 UTC

Lines Changed: +2, -2