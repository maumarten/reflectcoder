from reflectcoder.agents.base import Agent
from reflectcoder.agents.reflective import ReflectiveAgent
from reflectcoder.agents.reflective_memory import ReflectiveMemoryAgent
from reflectcoder.agents.stub import StubAgent

AGENT_REGISTRY: dict[str, type[Agent]] = {
    "stub": StubAgent,
    "reflective": ReflectiveAgent,
    "reflective-memory": ReflectiveMemoryAgent,
}

__all__ = [
    "AGENT_REGISTRY",
    "Agent",
    "ReflectiveAgent",
    "ReflectiveMemoryAgent",
    "StubAgent",
]
