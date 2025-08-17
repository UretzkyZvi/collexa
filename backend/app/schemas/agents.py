from pydantic import BaseModel


class CreateAgentRequest(BaseModel):
    brief: str


class Agent(BaseModel):
    agent_id: str
    display_name: str | None = None
    capabilities: list[str] = []
