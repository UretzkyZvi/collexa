from sqlalchemy import Column, String, DateTime, Text, JSON, Integer
from sqlalchemy.sql import func
from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String(64), primary_key=True)
    email = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Org(Base):
    __tablename__ = "orgs"
    id = Column(String(64), primary_key=True)
    name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OrgMember(Base):
    __tablename__ = "org_members"
    org_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), primary_key=True)
    role = Column(String(32), nullable=False, default="member")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


class Agent(Base):
    __tablename__ = "agents"
    id = Column(String(64), primary_key=True)
    org_id = Column(String(64))
    created_by = Column(String(64))
    display_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Run(Base):
    __tablename__ = "runs"
    id = Column(String(64), primary_key=True)
    agent_id = Column(String(64), nullable=False)
    org_id = Column(String(64))
    invoked_by = Column(String(64))
    status = Column(String(32), nullable=False, default="queued")
    input = Column(JSON)
    output = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False)
    level = Column(String(16), nullable=False, default="info")
    message = Column(Text, nullable=False)
    ts = Column(DateTime(timezone=True), server_default=func.now())


class AgentKey(Base):
    __tablename__ = "agent_keys"
    id = Column(String(64), primary_key=True)
    org_id = Column(String(64), nullable=False)
    agent_id = Column(String(64), nullable=False)
    name = Column(String(255))  # optional label
    key_hash = Column(String(128), nullable=False)
    created_by = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class A2AManifest(Base):
    __tablename__ = "a2a_manifests"
    id = Column(String(128), primary_key=True)  # agent_id:key_id or UUID
    agent_id = Column(String(64), nullable=False)
    version = Column(String(16), nullable=False)
    manifest_json = Column(JSON, nullable=False)
    signature = Column(Text)
    key_id = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(String(64), nullable=False)
    actor_id = Column(String(64))  # user_id or "api_key" for API key auth
    endpoint = Column(String(255), nullable=False)  # e.g., "POST /v1/agents/{id}/invoke"
    agent_id = Column(String(64))  # if applicable
    capability = Column(String(255))  # if applicable (from invoke payload)
    status_code = Column(Integer, nullable=False)
    request_id = Column(String(64))  # for correlation
    ip_address = Column(String(45))  # IPv4/IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
