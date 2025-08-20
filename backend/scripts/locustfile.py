import os
import random
from locust import HttpUser, task, between, events

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
STACK_TOKEN = os.getenv("STACK_ACCESS_TOKEN", "")
TEAM_ID = os.getenv("TEAM_ID", "")
AGENT_A_ID = os.getenv("AGENT_A_ID", "agent-a")
AGENT_B_ID = os.getenv("AGENT_B_ID", "agent-b")


def auth_headers():
    headers = {}
    if STACK_TOKEN:
        headers["Authorization"] = f"Bearer {STACK_TOKEN}"
    if TEAM_ID:
        headers["X-Team-Id"] = TEAM_ID
    return headers


class AgentUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task(3)
    def single_agent_invoke(self):
        agent_id = os.getenv("SINGLE_AGENT_ID", AGENT_A_ID)
        payload = {"capability": "echo", "input": {"msg": "hello"}}
        with self.client.post(
            f"/v1/agents/{agent_id}/invoke",
            json=payload,
            headers=auth_headers(),
            name="SingleAgentInvoke",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Status {resp.status_code}: {resp.text}")
            else:
                resp.success()

    @task(2)
    def cross_agent_invoke(self):
        # Invoke A with a payload that causes it to trigger B (if your app supports it).
        # For baseline, we just call A; customize to hit a true cross-agent path.
        payload = {"capability": "cross-call", "input": {"target_agent": AGENT_B_ID}}
        with self.client.post(
            f"/v1/agents/{AGENT_A_ID}/invoke",
            json=payload,
            headers=auth_headers(),
            name="CrossAgentInvoke",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Status {resp.status_code}: {resp.text}")
            else:
                resp.success()


@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--run-time", type=str, default=os.getenv("RUN_TIME", "1m"))
    parser.add_argument("--users", type=int, default=int(os.getenv("USERS", "5")))
    parser.add_argument("--spawn-rate", type=float, default=float(os.getenv("SPAWN_RATE", "2")))

