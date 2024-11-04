Last Updated: 2024-11-01 15:33:10 UTC

Lines Changed: +22, -0

# Setup

This guide will take you through environment setup in order to run the codebase locally and contribute to our project.
It's recommended that you use MacOS, Unix, or Linux as an operating system for development; we do not support nor provide instructions for Windows systems and development.

## [Github Repository](https://github.com)

```shell
# HTTPS
git clone https://github.com/abstractoperators/concrete.git

# SSH
git clone git@github.com:abstractoperators/concrete.git
```

## [uv](https://docs.astral.sh/uv/getting-started/)

Concrete uses uv for dependency management and environment isolation.

### Installation
> We recommend the official [installation instructions](https://docs.astral.sh/uv/getting-started/installation/)

Abbreviated installation:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh 
```

### Python Version

uv handles Python versions for you. 

Install a specific python version using `uv python install 3.11`

Pin that version using `uv python pin 3.11`

### Projects

Initialize a project in your working directory using

```shell
uv init
```

uv creates a `.venv` and `uv.lock` file in the root of your project the first time you run a project command (`uv run`, `uv sync`, `uv lock` ...)

Projects may define a `[build-system]`.
The presence of a build-system determines whether the project will be installed in the project's virtual environment. If it is not present, only its dependencies will be installed.

To build a project, use `uv build`

#### `pyproject.toml`

`pyproject.toml` contains metadata about your project.
You can edit this file manually, or use commands like `uv add` to manage the project from the terminal.

```toml

[project]
name = "hello-world"
version = "0.1.0"
description = "Add your description here"
```

#### Manage Dependencies

To add a dependency, run `uv add <package-name>[==x.y.z]`. It is NOT recommended to manually add the environment manually (e.g. `uv pip install <package>`). To make it an optional dependency, use `uv add <package-name> --optional <optional-group>`.

To remove a dependency, run `uv remove <package-name>`.

To run a command in your virtual environment, use `uv run <command>`. Alternatively, you activate the virtual environment.

Sync your environment with your specified requirements using `uv sync --extra <optional-group>`

#### `uv.lock`

Unlike `pyproject.toml`, the lockfile contains exact resolved versions that are installed in your project environment. It's created and updated during invocations using the project environment (`uv sync` and `uv run`). You may also explicitly update it using `uv lock`.

`uv.lock` should NOT be manually edited.

> You can export `uv.lock` to a `requirements.txt` with `uv export --format requirements-txt`.

#### Workspaces

Workspaces are a collection of one or more packages. They organize large codebases by splitting them into multiple packages with common dependencies.

Each package in a workspace defines its own `pyproject.toml`, but the workspace shares a single lockfile, ensuring consistent dependencies across all packages.

Create a workspace by adding a `[tool.uv.workspace]` to your root `pyproject.toml`. The root is also a member of the workspace.

```toml
[tool.uv.workspace]
members = ["package1", "package2"] # Required
exclude = ["package3"] # Optional
```

Directories included by the members glob must contain a `pyproject.toml`

`uv lock` operates on the entire workspace, while `uv run` and `uv sync` can be run on individual packages using the `--package` argument.

Dependencies on workspace members are specified via `[tool.uv.sources]`. 

```toml
[project]
...
dependencies = ['bird-feeder'] # Indicate that the project depends on the bird-feeder package

[tool.uv.sources]
bird-feeder = { workspace = true} # Indicates that bird-feeder can be found in the workspace.
# tqdm = { git = "https://github.com/tqdm/tqdm" }
```

#### Git Workflow

In addition to package and dependency management, we use uv to augment the developer git workflow.
The following command will install the correct dependencies to run `concrete` locally as well as the precommit packages to pass our PR validations.
In the root folder of the repository:

```shell
make install
```

If you find yourself needing to run the pre-commit manually, use the following:

```shell
uv run pre-commit run --all-files
```

and to skip pre-commit hooks for whatever reason, use

```shell
git commit -m "Pass butter" --no-verify
```

## [Environment Variables]

We recommend you store all of the relevant environment variables into a `.env` file
located in the root directory of `concrete`.
A full `.env` developer example can be found [in our repository](https://github.com/abstractoperators/concrete/blob/02cc58605f5b0b507434985ef2bd3ed7bb7e3881/.env.example).

Be sure to set the `ENV` variable as necessary:

```shell
ENV=DEV
# for development
```

or

```shell
ENV=PRODUCTION
# for production
```

## [OpenAI](https://openai.com/index/openai-api/)

By default, operators rely on OpenAI ChatGPT 4 models to process queries. OpenAI requires a key to access its API:

```shell
OPENAI_API_KEY=<your api key here>
```
