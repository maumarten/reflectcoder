from reflectcoder.agents.base import Agent
from reflectcoder.agents.reflective import ReflectiveAgent
from reflectcoder.agents.stub import StubAgent

AGENT_REGISTRY: dict[str, type[Agent]] = {
    "stub": StubAgent,
    "reflective": ReflectiveAgent,
}

__all__ = ["Agent", "ReflectiveAgent", "StubAgent", "AGENT_REGISTRY"]
