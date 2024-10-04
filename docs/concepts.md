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

**Daemons**
`Daemons` are long-running processes providing an entrypoint for Operators and Tools to interact.
# Module Documentation

**[Base](base.md)**  
`Base` is the foundational class for all models in this module, providing a standardized representation method for instances.

**[MetadataMixin](metadata_mixin.md)**  
`MetadataMixin` adds a unique identifier (`id`) to models, ensuring each instance can be uniquely identified.

## Relationship Models

**[OperatorToolLink](operator_tool_link.md)**  
`OperatorToolLink` is a linking model that establishes a many-to-many relationship between `Operator` and `Tool` models, allowing operators to utilize multiple tools and vice versa.

## Orchestrator Models

**[OrchestratorBase](orchestrator_base.md)**  
`OrchestratorBase` serves as the base class for orchestrators, defining common attributes such as `type_name`, `title`, and `owner`.

**[OrchestratorUpdate](orchestrator_update.md)**  
`OrchestratorUpdate` is used for updating existing orchestrator instances, allowing modifications to the `title` and `owner` fields.

**[OrchestratorCreate](orchestrator_create.md)**  
`OrchestratorCreate` extends `OrchestratorBase` for creating new orchestrator instances with required attributes.

**[Orchestrator](orchestrator.md)**  
`Orchestrator` represents a specific orchestrator instance, maintaining relationships with `Operator` instances and supporting cascading deletions.

## Operator Models

**[OperatorBase](operator_base.md)**  
`OperatorBase` defines the foundational attributes for operators, including `instructions`, `title`, and a foreign key reference to the owning orchestrator.

**[OperatorUpdate](operator_update.md)**  
`OperatorUpdate` allows for the modification of existing operator instances, focusing on `instructions` and `title` attributes.

**[OperatorCreate](operator_create.md)**  
`OperatorCreate` is used for creating new operator instances, inheriting from `OperatorBase`.

**[Operator](operator.md)**  
`Operator` represents a specific operator instance, linking to `Client` and `Tool` models, and establishing a relationship with its owning `Orchestrator`.

## Client Models

**[ClientBase](client_base.md)**  
`ClientBase` defines the basic attributes for clients, including `client` name, `temperature`, and `model`, along with foreign key references to the orchestrator and operator.

**[ClientUpdate](client_update.md)**  
`ClientUpdate` is used for updating existing client instances, allowing changes to `client`, `temperature`, and `model` attributes.

**[ClientCreate](client_create.md)**  
`ClientCreate` extends `ClientBase` for creating new client instances.

**[Client](client.md)**  
`Client` represents a specific client instance, maintaining a relationship with its owning `Operator`.

## Tool Models

**[ToolBase](tool_base.md)**  
`ToolBase` serves as the base class for tools, defining common attributes and behaviors for all tool instances.

**[ToolUpdate](tool_update.md)**  
`ToolUpdate` allows for the modification of existing tool instances.

**[ToolCreate](tool_create.md)**  
`ToolCreate` is used for creating new tool instances, inheriting from `ToolBase`.

**[Tool](tool.md)**  
`Tool` represents a specific tool instance, linking to `Operator` instances through the `OperatorToolLink` model.

## Message Models

**[MessageBase](message_base.md)**  
`MessageBase` defines the foundational attributes for messages, including `type_name`, `content`, `prompt`, and `status`, along with a foreign key reference to the orchestrator.

**[MessageUpdate](message_update.md)**  
`MessageUpdate` allows for the modification of existing message instances, focusing on the `status` attribute.

**[MessageCreate](message_create.md)**  
`MessageCreate` is used for creating new message instances, inheriting from `MessageBase`.

**[Message](message.md)**  
`Message` represents a specific message instance, including metadata through `MetadataMixin`.

## Knowledge Graph Models

**[NodeBase](node_base.md)**  
`NodeBase` serves as the base model for nodes in the knowledge graph, defining a potential parent-child relationship through `parent_id`.

**[NodeUpdate](node_update.md)**  
`NodeUpdate` allows for the modification of existing node instances, focusing on the `parent_id` attribute.

**[NodeCreate](node_create.md)**  
`NodeCreate` is used for creating new node instances, inheriting from `NodeBase`.

**[Node](node.md)**  
`Node` represents a specific node instance in the knowledge graph, maintaining relationships with child nodes.

## Repository Node Models

**[RepoNodeBase](repo_node_base.md)**  
`RepoNodeBase` defines the foundational attributes for repository nodes, including organization, repository name, and node type.

**[RepoNodeUpdate](repo_node_update.md)**  
`RepoNodeUpdate` allows for the modification of existing repository node instances, focusing on various attributes such as `org`, `repo`, and `name`.

**[RepoNodeCreate](repo_node_create.md)**  
`RepoNodeCreate` is used for creating new repository node instances, inheriting from `RepoNodeBase`.

**[RepoNode](repo_node.md)**  
`RepoNode` represents a specific repository node instance, maintaining relationships with child nodes and supporting composite indexing on `org` and `repo`.