# Concrete
Concrete is an all-in-one, minimal, and open source agent framework *and platform* for building intuitive, composable agents.
It is unopinionated, and meant to be used as a default or "starter" agent framework for Abstract Operators' partners and affiliates.

## How To Use Concrete
There are three primary ways to start using concrete.  
1. SDK - Use concrete from CLIs, scripts, or notebooks.
2. API Server - Host concrete's API app that can be a standalone webservice for defining, developing, and serving agents in your distributed architecture.  
3. Cloud-Hosted Consumer Platform - Use our platform to let your users and community developer, serve, and monetize their agents. Contact us at hello@abstractoperators.ai for partnerships.

## Plugins and Integrations
There are two levels of integrations that concrete supports: agent-level and systems-level.

At the agent level, integrations are primarily facilitated by function calling and tool use. See src/concrete-core/concrete/tools for more info.

At the systems-level, Abstract Operators has and will develop structural integrations for things of a similar nature to: (1) suporting async calls (see src/concrete-async) and (2) for saving Agents, Agent messages, and orchestrations persistently in db (see src/concrete-db).

## SDK
### Installation

```python
pip install "concrete[openai]"
```

### Quickstart

```bash
export OPENAI_API_KEY=<your-api-key-here>
python -m concrete-core prompt "Create a simple program that says 'Hello, World!'"
```

Last Updated: 2025-05-04 17:22:19 UTC
Lines Changed: +18, -2
