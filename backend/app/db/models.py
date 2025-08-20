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


class BillingCustomer(Base):
    """Internal customer representation - maps to external provider"""
    __tablename__ = "billing_customers"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(64), ForeignKey("orgs.id"), nullable=False)
    provider = Column(String(32), nullable=False)  # "stripe", "paypal", etc.
    external_customer_id = Column(String(255), nullable=False)  # Provider's customer ID
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    metadata_json = Column('metadata', JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BillingSubscription(Base):
    """Internal subscription representation"""
    __tablename__ = "billing_subscriptions"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(64), ForeignKey("billing_customers.id"), nullable=False)
    external_subscription_id = Column(String(255), nullable=False)
    plan_id = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    metadata_json = Column('metadata', JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BillingEvent(Base):
    """Provider-agnostic billing events for audit trail"""
    __tablename__ = "billing_events"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(64), ForeignKey("orgs.id"), nullable=False)
    customer_id = Column(String(64), ForeignKey("billing_customers.id"))
    event_type = Column(String(64), nullable=False)  # "subscription.created", "payment.succeeded"
    provider = Column(String(32), nullable=False)
    external_event_id = Column(String(255))  # Provider's event ID
    amount_cents = Column(Integer)
    metadata_json = Column('metadata', JSON)
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Budget(Base):
    """Budget limits and alerts for organizations and agents"""
    __tablename__ = "budgets"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(64), ForeignKey("orgs.id"), nullable=False)
    agent_id = Column(String(64), ForeignKey("agents.id"), nullable=True)  # NULL = org-level budget
    period = Column(String(32), nullable=False)  # "monthly", "daily", "weekly"
    limit_cents = Column(Integer, nullable=False)  # Budget limit in cents
    current_usage_cents = Column(Integer, nullable=False, default=0)  # Current period usage
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    alerts_json = Column(JSON)  # Alert configuration (thresholds, channels)
    enforcement_mode = Column(String(16), nullable=False, default="soft")  # "soft", "hard"
    status = Column(String(16), nullable=False, default="active")  # "active", "exceeded", "disabled"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UsageRecord(Base):
    """Usage tracking for billing and budget enforcement"""
    __tablename__ = "usage_records"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(64), ForeignKey("orgs.id"), nullable=False)
    agent_id = Column(String(64), ForeignKey("agents.id"), nullable=True)
    run_id = Column(String(64), ForeignKey("runs.id"), nullable=True)
    usage_type = Column(String(32), nullable=False)  # "invocation", "tokens", "storage"
    quantity = Column(Integer, nullable=False)  # Number of units used
    cost_cents = Column(Integer, nullable=False)  # Cost in cents
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    billing_period = Column(String(32), nullable=False)  # "2025-01" for monthly billing
    metadata_json = Column('metadata', JSON)  # Additional usage metadata


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
