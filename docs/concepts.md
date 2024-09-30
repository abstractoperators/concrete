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

**[FastAPI Application](app.md)**  
The FastAPI application serves as the main entry point for the web interface of the Abstract Operators module. It provides routes for rendering templates and handling user interactions.

**Endpoints**  

**`GET /`**  
The root endpoint renders the main index page of the application. It utilizes Jinja2 templates to serve the HTML content to the user.

**`GET /chat`**  
This endpoint renders a group chat interface. It currently returns a static list of messages from various operators, which can be made dynamic in future iterations. The response is generated using a Jinja2 template.

**`GET /orchestrators`**  
This endpoint retrieves a list of orchestrators from the database using the CRUD operations defined in the `crud` module. It constructs an HTML response that displays each orchestrator in a card format, including an avatar and title. The orchestrators are fetched within a session context to ensure proper database handling.

**Static Files**  
The application serves static files (e.g., images, CSS) from the `/static` directory, allowing for a richer user interface.

**Templates**  
The application uses Jinja2 for templating, with templates stored in the `/templates` directory. This allows for dynamic content rendering based on the data provided by the application logic.