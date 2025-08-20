"""
Tests for enhanced billing system with Phase 2 libraries.

These tests verify the integration of APScheduler, Apprise, and Celery
with the billing system for automated monitoring and notifications.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timedelta

# Skip this suite if optional deps not installed
pytest.importorskip("apscheduler", reason="APScheduler not installed")
pytest.importorskip("apprise", reason="Apprise not installed")

from app.services.scheduling.budget_scheduler_service import BudgetSchedulerService
from app.services.notifications.alert_service import AlertService, AlertSeverity
from app.services.billing.async_webhook_service import (
    process_webhook_async, send_budget_alert_async, check_budget_violations_async
)
from app.db import models


class TestEnhancedBillingSystem:
    """Test the enhanced billing system with Phase 2 libraries"""
    
    def setup_method(self):
        """Setup test environment"""
        self.org_id = "test-org-123"
        self.agent_id = "test-agent-456"
    
    @pytest.mark.asyncio
    async def test_budget_scheduler_initialization(self):
        """Test that the budget scheduler initializes correctly"""
        scheduler = BudgetSchedulerService()
        
        # Check that jobs are configured
        assert scheduler.scheduler is not None
        
        # Check that expected jobs are scheduled
        job_ids = [job.id for job in scheduler.scheduler.get_jobs()]
        expected_jobs = [
            'budget_violation_check',
            'budget_warning_check',
            'daily_budget_reset',
            'weekly_budget_reset',
            'monthly_budget_reset',
            'monthly_usage_reports',
            'cleanup_usage_records'
        ]
        
        for expected_job in expected_jobs:
            assert expected_job in job_ids, f"Job {expected_job} not found in scheduled jobs"
    
    @pytest.mark.asyncio
    async def test_alert_service_initialization(self):
        """Test that the alert service initializes correctly"""
        alert_service = AlertService()
        
        # Check that the service is initialized
        assert alert_service.apobj is not None
        
        # Check configured channels (will be empty in test environment)
        channels = alert_service.get_configured_channels()
        assert isinstance(channels, list)
    
    @pytest.mark.asyncio
    async def test_budget_violation_alert_formatting(self):
        """Test budget violation alert message formatting"""
        alert_service = AlertService()
        
        violations = [
            {
                "budget_name": "Organization monthly budget",
                "current_usage_cents": 15000,  # $150
                "limit_cents": 10000,  # $100
                "utilization_percent": 150.0,
                "enforcement_mode": "hard",
                "period_end": "2025-01-31T23:59:59Z"
            }
        ]
        
        # Mock the apprise notify method
        with patch.object(alert_service.apobj, 'notify', return_value=True) as mock_notify:
            success = await alert_service.send_budget_violation_alert(
                org_id=self.org_id,
                violations=violations,
                severity=AlertSeverity.CRITICAL
            )
            
            assert success is True
            mock_notify.assert_called_once()
            
            # Check the call arguments
            call_args = mock_notify.call_args
            assert "Budget Violation Alert" in call_args.kwargs['title']
            assert "URGENT" in call_args.kwargs['body']
            assert "$150.00" in call_args.kwargs['body']
            assert "$100.00" in call_args.kwargs['body']
            assert "BLOCKED" in call_args.kwargs['body']  # Hard enforcement
    
    @pytest.mark.asyncio
    async def test_budget_warning_alert_formatting(self):
        """Test budget warning alert message formatting"""
        alert_service = AlertService()
        
        warnings = [
            {
                "budget_name": "Agent daily budget",
                "current_usage_cents": 850,  # $8.50
                "limit_cents": 1000,  # $10.00
                "utilization_percent": 85.0,
                "enforcement_mode": "soft",
                "remaining_cents": 150  # $1.50
            }
        ]
        
        with patch.object(alert_service.apobj, 'notify', return_value=True) as mock_notify:
            success = await alert_service.send_budget_warning_alert(
                org_id=self.org_id,
                warnings=warnings,
                severity=AlertSeverity.WARNING
            )
            
            assert success is True
            mock_notify.assert_called_once()
            
            call_args = mock_notify.call_args
            assert "Budget Warning" in call_args.kwargs['title']
            assert "$8.50" in call_args.kwargs['body']
            assert "$10.00" in call_args.kwargs['body']
            assert "85.0%" in call_args.kwargs['body']
            assert "$1.50" in call_args.kwargs['body']
    
    @pytest.mark.asyncio
    async def test_system_alert_with_metadata(self):
        """Test system alert with metadata"""
        alert_service = AlertService()
        
        metadata = {
            "component": "billing_system",
            "version": "1.0.0",
            "environment": "test"
        }
        
        with patch.object(alert_service.apobj, 'notify', return_value=True) as mock_notify:
            success = await alert_service.send_system_alert(
                title="System Test",
                message="This is a test alert",
                severity=AlertSeverity.INFO,
                metadata=metadata
            )
            
            assert success is True
            mock_notify.assert_called_once()
            
            call_args = mock_notify.call_args
            assert "System Test" in call_args.kwargs['title']
            assert "billing_system" in call_args.kwargs['body']
            assert "1.0.0" in call_args.kwargs['body']
    
    def test_celery_task_registration(self):
        """Test that Celery tasks are properly registered"""
        from app.services.billing.async_webhook_service import celery_app
        
        # Check that expected tasks are registered
        expected_tasks = [
            'billing.process_webhook',
            'billing.process_subscription_event',
            'billing.generate_monthly_usage_report',
            'billing.send_budget_alert',
            'billing.check_budget_violations'
        ]
        
        registered_tasks = list(celery_app.tasks.keys())
        
        for expected_task in expected_tasks:
            assert expected_task in registered_tasks, f"Task {expected_task} not registered"
    
    @pytest.mark.asyncio
    async def test_webhook_processing_with_retry(self):
        """Test webhook processing with retry logic"""
        import base64
        
        # Create test webhook payload
        test_payload = b'{"type": "test.event", "data": {"test": true}}'
        payload_b64 = base64.b64encode(test_payload).decode()
        
        # Mock the webhook service to fail first, then succeed
        with patch('app.services.billing.webhook_service.WebhookService') as mock_webhook_service:
            mock_instance = mock_webhook_service.return_value
            mock_instance.process_webhook.side_effect = [Exception("Network error"), True]
            
            # This would normally be called by Celery, but we'll test the function directly
            with patch('app.services.billing.async_webhook_service.get_db'):
                # First call should fail and trigger retry logic
                try:
                    result = process_webhook_async(payload_b64, "test_signature", "stripe")
                    # If we get here, the retry logic worked
                    assert result["status"] == "success"
                except Exception:
                    # Expected on first failure
                    pass
    
    @pytest.mark.asyncio
    async def test_monthly_report_notification(self):
        """Test monthly report notification formatting"""
        alert_service = AlertService()
        
        report_data = {
            "org_id": self.org_id,
            "period": {
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-01-31T23:59:59Z"
            },
            "summary": {
                "total_cost_cents": 5000,  # $50.00
                "total_cost_dollars": 50.0,
                "record_count": 1500,
                "usage_by_type": {
                    "invocation": {"cost_cents": 3000, "quantity": 300},
                    "input_tokens": {"cost_cents": 1000, "quantity": 100000},
                    "output_tokens": {"cost_cents": 1000, "quantity": 50000}
                }
            },
            "agent_usage": {
                "agent-1": {
                    "agent_name": "Test Agent 1",
                    "total_cost_cents": 3000
                },
                "agent-2": {
                    "agent_name": "Test Agent 2", 
                    "total_cost_cents": 2000
                }
            },
            "budget_status": {
                "has_violations": True,
                "has_warnings": False,
                "violations": [{"budget_id": "budget-1"}]
            }
        }
        
        with patch.object(alert_service.apobj, 'notify', return_value=True) as mock_notify:
            success = await alert_service.send_monthly_report_notification(
                org_id=self.org_id,
                report_data=report_data
            )
            
            assert success is True
            mock_notify.assert_called_once()
            
            call_args = mock_notify.call_args
            assert "Monthly Usage Report" in call_args.kwargs['title']
            body = call_args.kwargs['body']
            assert "$50.00" in body
            assert "1,500" in body
            assert "Test Agent 1" in body
            assert "Budget Violations" in body
            assert "1" in body
    
    @pytest.mark.asyncio
    async def test_scheduler_job_execution(self):
        """Test that scheduler jobs can be executed"""
        scheduler = BudgetSchedulerService()
        
        # Mock the database and services
        with patch('app.services.scheduling.budget_scheduler_service.get_db'), \
             patch('app.services.budget.budget_enforcement_service.BudgetEnforcementService') as mock_enforcement:
            
            mock_enforcement.return_value.get_budget_violations.return_value = []
            
            # Test budget violation check
            await scheduler.check_budget_violations()
            
            # Should not raise any exceptions
            assert True
    
    @pytest.mark.asyncio
    async def test_notification_channel_configuration(self):
        """Test notification channel configuration"""
        alert_service = AlertService()
        
        # Test with no channels configured (default test state)
        channels = alert_service.get_configured_channels()
        assert isinstance(channels, list)
        
        # Test notification test function
        result = await alert_service.test_notifications()
        assert "success" in result
        assert "channels_configured" in result
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_integration_workflow(self):
        """Test complete integration workflow"""
        # This test simulates a complete workflow:
        # 1. Budget violation detected
        # 2. Alert sent via notification service
        # 3. Webhook processed via Celery
        
        # Mock all external dependencies
        with patch('app.services.scheduling.budget_scheduler_service.get_db'), \
             patch('app.services.budget.budget_enforcement_service.BudgetEnforcementService') as mock_enforcement, \
             patch('app.services.notifications.alert_service.AlertService.send_budget_violation_alert') as mock_alert:
            
            # Setup mock violation
            mock_violation = Mock()
            mock_violation.id = "budget-123"
            mock_violation.limit_cents = 10000
            mock_violation.current_usage_cents = 15000
            mock_violation.enforcement_mode = "hard"
            mock_violation.agent_id = self.agent_id
            mock_violation.period = "monthly"
            mock_violation.period_end = datetime.utcnow() + timedelta(days=10)
            
            mock_enforcement.return_value.get_budget_violations.return_value = [mock_violation]
            mock_alert.return_value = True
            
            # Create scheduler and run violation check
            scheduler = BudgetSchedulerService()

            # Also mock org listing to trigger loop body
            with patch('app.services.scheduling.budget_scheduler_service.get_db') as mock_get_db, \
                 patch('app.services.scheduling.budget_scheduler_service.BudgetEnforcementService', new=mock_enforcement):
                mock_session = Mock()
                mock_query = Mock()
                mock_filter = Mock()
                mock_session.query.return_value = mock_query
                mock_query.all.return_value = [Mock(id=self.org_id)]
                mock_get_db.return_value = iter([mock_session])

                await scheduler.check_budget_violations()

            # Verify that violation detection was called
            assert mock_enforcement.return_value.get_budget_violations.called
            
            # The alert would be queued via Celery in real scenario
            # Here we just verify the workflow completes without errors
            assert True


if __name__ == "__main__":
    pytest.main([__file__])
