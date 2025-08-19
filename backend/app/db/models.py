from sqlalchemy import Column, String, DateTime, Text, JSON, Integer, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base
import uuid


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


class Sandbox(Base):
    __tablename__ = "sandboxes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(String, ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    mode = Column(String, nullable=False)  # mock, emulated, connected
    target_system = Column(String, nullable=True)
    config_json = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="created")  # created, running, stopped, error
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    runs = relationship("SandboxRun", back_populates="sandbox", cascade="all, delete-orphan")


class SandboxRun(Base):
    __tablename__ = "sandbox_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sandbox_id = Column(String, ForeignKey("sandboxes.id", ondelete="CASCADE"), nullable=False)
    phase = Column(String, nullable=False)  # learn, eval
    task_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="running")  # running, completed, failed
    input_json = Column(JSON, nullable=True)
    output_json = Column(JSON, nullable=True)
    error_json = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    sandbox = relationship("Sandbox", back_populates="runs")


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    target_system = Column(String, nullable=True)
    objectives_json = Column(JSON, nullable=True)
    curriculum_json = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="draft")  # draft, active, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CapabilityAssessment(Base):
    __tablename__ = "capability_assessments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    target_system = Column(String, nullable=True)
    rubric_json = Column(JSON, nullable=True)
    score = Column(Float, nullable=True)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    evidence_run_ids = Column(JSON, nullable=True)  # Store as JSON array for SQLite compatibility
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
