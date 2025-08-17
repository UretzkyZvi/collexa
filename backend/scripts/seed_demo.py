import os
import uuid
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

# Minimal seed: one org, one user, membership, and one agent
org_id = str(uuid.uuid4())
user_id = str(uuid.uuid4())
agent_id = str(uuid.uuid4())

with engine.begin() as conn:
    conn.execute(
        """
        insert into orgs (id, name) values (%s, %s)
        on conflict (id) do nothing
        """,
        (org_id, "Demo Org"),
    )
    conn.execute(
        """
        insert into users (id, email) values (%s, %s)
        on conflict (id) do nothing
        """,
        (user_id, "demo@example.com"),
    )
    conn.execute(
        """
        insert into org_members (org_id, user_id, role) values (%s, %s, %s)
        on conflict (org_id, user_id) do nothing
        """,
        (org_id, user_id, "owner"),
    )
    conn.execute(
        """
        insert into agents (id, org_id, created_by, display_name) values (%s, %s, %s, %s)
        on conflict (id) do nothing
        """,
        (agent_id, org_id, user_id, "Demo Agent"),
    )

print("Seeded demo data:")
print({"org_id": org_id, "user_id": user_id, "agent_id": agent_id})
