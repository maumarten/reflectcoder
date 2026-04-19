from reflectcoder.agents.base import Agent
from reflectcoder.agents.stub import StubAgent

AGENT_REGISTRY: dict[str, type[Agent]] = {
    "stub": StubAgent,
}

__all__ = ["Agent", "StubAgent", "AGENT_REGISTRY"]
