"""
Multi-channel alert service using Apprise.

This service provides notifications through multiple channels including
email, Slack, Discord, webhooks, and more for budget alerts and system events.
"""

import apprise
from typing import List, Dict, Any, Optional
from enum import Enum
import logging
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Available alert channels"""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    TEAMS = "teams"


class AlertService:
    """Service for sending multi-channel notifications"""
    
    def __init__(self):
        self.apobj = apprise.Apprise()
        self.setup_channels()
    
    def setup_channels(self):
        """Configure notification channels from environment variables"""
        channels_added = 0
        
        # Email (SMTP)
        if all([settings.SMTP_SERVER, settings.SMTP_USER, settings.SMTP_PASS]):
            smtp_url = f'mailto://{settings.SMTP_USER}:{settings.SMTP_PASS}@{settings.SMTP_SERVER}'
            if settings.SMTP_PORT:
                smtp_url += f':{settings.SMTP_PORT}'
            if settings.SMTP_TO:
                smtp_url += f'?to={settings.SMTP_TO}'
            
            self.apobj.add(smtp_url)
            channels_added += 1
            logger.info("Email notifications configured")
        
        # Slack
        if settings.SLACK_WEBHOOK_URL:
            self.apobj.add(settings.SLACK_WEBHOOK_URL)
            channels_added += 1
            logger.info("Slack notifications configured")
        
        # Discord
        if settings.DISCORD_WEBHOOK_URL:
            self.apobj.add(settings.DISCORD_WEBHOOK_URL)
            channels_added += 1
            logger.info("Discord notifications configured")
        
        # Microsoft Teams
        if settings.TEAMS_WEBHOOK_URL:
            self.apobj.add(settings.TEAMS_WEBHOOK_URL)
            channels_added += 1
            logger.info("Teams notifications configured")
        
        # Custom webhook
        if settings.CUSTOM_WEBHOOK_URL:
            self.apobj.add(settings.CUSTOM_WEBHOOK_URL)
            channels_added += 1
            logger.info("Custom webhook notifications configured")
        
        if channels_added == 0:
            logger.warning("No notification channels configured")
        else:
            logger.info(f"Configured {channels_added} notification channels")
    
    async def send_budget_violation_alert(
        self, 
        org_id: str, 
        violations: List[Dict[str, Any]],
        severity: AlertSeverity = AlertSeverity.CRITICAL
    ) -> bool:
        """
        Send budget violation alert.
        
        Args:
            org_id: Organization ID
            violations: List of budget violations
            severity: Alert severity level
            
        Returns:
            True if alert was sent successfully
        """
        try:
            # Determine emoji and color based on severity
            emoji = "🚨" if severity == AlertSeverity.CRITICAL else "⚠️"
            
            title = f"{emoji} Budget Violation Alert - Organization {org_id}"
            
            body = self._format_violation_message(violations)
            
            # Add footer with timestamp
            body += f"\n\n📅 Alert generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            body += f"\n🏢 Organization: {org_id}"
            
            # Send notification
            success = self.apobj.notify(title=title, body=body)
            
            if success:
                logger.info(f"Budget violation alert sent for org {org_id}")
            else:
                logger.error(f"Failed to send budget violation alert for org {org_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending budget violation alert for org {org_id}: {e}")
            return False
    
    async def send_budget_warning_alert(
        self, 
        org_id: str, 
        warnings: List[Dict[str, Any]],
        severity: AlertSeverity = AlertSeverity.WARNING
    ) -> bool:
        """
        Send budget warning alert.
        
        Args:
            org_id: Organization ID
            warnings: List of budget warnings
            severity: Alert severity level
            
        Returns:
            True if alert was sent successfully
        """
        try:
            title = f"⚠️ Budget Warning - Organization {org_id}"
            
            body = "The following budgets are approaching their limits:\n\n"
            
            for warning in warnings:
                body += f"📊 **{warning['budget_name']}**\n"
                body += f"   💰 Usage: ${warning['current_usage_cents']/100:.2f} / ${warning['limit_cents']/100:.2f}\n"
                body += f"   📈 Utilization: {warning['utilization_percent']:.1f}%\n"
                body += f"   🔒 Enforcement: {warning['enforcement_mode']}\n"
                if warning.get('remaining_cents'):
                    body += f"   💸 Remaining: ${warning['remaining_cents']/100:.2f}\n"
                body += "\n"
            
            body += "💡 **Recommended Actions:**\n"
            body += "• Review current usage patterns\n"
            body += "• Consider increasing budget limits if needed\n"
            body += "• Monitor usage more closely\n"
            
            # Add footer
            body += f"\n📅 Alert generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            body += f"\n🏢 Organization: {org_id}"
            
            success = self.apobj.notify(title=title, body=body)
            
            if success:
                logger.info(f"Budget warning alert sent for org {org_id}")
            else:
                logger.error(f"Failed to send budget warning alert for org {org_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending budget warning alert for org {org_id}: {e}")
            return False
    
    async def send_system_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send general system alert.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            metadata: Additional metadata
            
        Returns:
            True if alert was sent successfully
        """
        try:
            # Add emoji based on severity
            emoji_map = {
                AlertSeverity.INFO: "ℹ️",
                AlertSeverity.WARNING: "⚠️",
                AlertSeverity.ERROR: "❌",
                AlertSeverity.CRITICAL: "🚨"
            }
            
            emoji = emoji_map.get(severity, "ℹ️")
            full_title = f"{emoji} {title}"
            
            body = message
            
            # Add metadata if provided
            if metadata:
                body += "\n\n📋 **Additional Information:**\n"
                for key, value in metadata.items():
                    body += f"• {key}: {value}\n"
            
            # Add timestamp
            body += f"\n📅 Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            success = self.apobj.notify(title=full_title, body=body)
            
            if success:
                logger.info(f"System alert sent: {title}")
            else:
                logger.error(f"Failed to send system alert: {title}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending system alert '{title}': {e}")
            return False
    
    async def send_monthly_report_notification(
        self,
        org_id: str,
        report_data: Dict[str, Any]
    ) -> bool:
        """
        Send monthly usage report notification.
        
        Args:
            org_id: Organization ID
            report_data: Usage report data
            
        Returns:
            True if notification was sent successfully
        """
        try:
            title = f"📊 Monthly Usage Report - Organization {org_id}"
            
            summary = report_data.get('summary', {})
            total_cost = summary.get('total_cost_dollars', 0)
            record_count = summary.get('record_count', 0)
            
            body = f"Your monthly usage report is ready!\n\n"
            body += f"💰 **Total Cost:** ${total_cost:.2f}\n"
            body += f"📈 **Usage Records:** {record_count:,}\n"
            
            # Usage breakdown
            usage_by_type = summary.get('usage_by_type', {})
            if usage_by_type:
                body += f"\n📊 **Usage Breakdown:**\n"
                for usage_type, data in usage_by_type.items():
                    cost = data.get('cost_cents', 0) / 100
                    quantity = data.get('quantity', 0)
                    body += f"• {usage_type.replace('_', ' ').title()}: ${cost:.2f} ({quantity:,} units)\n"
            
            # Agent usage
            agent_usage = report_data.get('agent_usage', {})
            if agent_usage:
                body += f"\n🤖 **Top Agents by Usage:**\n"
                sorted_agents = sorted(
                    agent_usage.items(), 
                    key=lambda x: x[1].get('total_cost_cents', 0), 
                    reverse=True
                )[:5]  # Top 5 agents
                
                for agent_id, data in sorted_agents:
                    agent_name = data.get('agent_name', agent_id)
                    cost = data.get('total_cost_cents', 0) / 100
                    body += f"• {agent_name}: ${cost:.2f}\n"
            
            # Budget status
            budget_status = report_data.get('budget_status', {})
            if budget_status.get('has_violations'):
                body += f"\n🚨 **Budget Violations:** {len(budget_status.get('violations', []))}\n"
            if budget_status.get('has_warnings'):
                body += f"⚠️ **Budget Warnings:** {len(budget_status.get('warnings', []))}\n"
            
            body += f"\n📅 Report Period: {report_data.get('period', {}).get('start', 'N/A')} to {report_data.get('period', {}).get('end', 'N/A')}"
            body += f"\n🏢 Organization: {org_id}"
            
            success = self.apobj.notify(title=title, body=body)
            
            if success:
                logger.info(f"Monthly report notification sent for org {org_id}")
            else:
                logger.error(f"Failed to send monthly report notification for org {org_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending monthly report notification for org {org_id}: {e}")
            return False
    
    def _format_violation_message(self, violations: List[Dict[str, Any]]) -> str:
        """Format budget violation message"""
        body = "🚨 **URGENT: Budget limits have been exceeded!**\n\n"
        
        for violation in violations:
            body += f"📊 **{violation['budget_name']}**\n"
            body += f"   💰 Usage: ${violation['current_usage_cents']/100:.2f} / ${violation['limit_cents']/100:.2f}\n"
            body += f"   📈 Utilization: {violation['utilization_percent']:.1f}%\n"
            body += f"   🔒 Enforcement: {violation['enforcement_mode']}\n"
            
            if violation['enforcement_mode'] == 'hard':
                body += f"   ⛔ **Status: BLOCKED** - New requests will be rejected\n"
            else:
                body += f"   ⚠️ **Status: WARNING** - Requests allowed but monitored\n"
            
            if violation.get('period_end'):
                body += f"   📅 Period ends: {violation['period_end']}\n"
            
            body += "\n"
        
        body += "🚨 **Immediate Action Required:**\n"
        body += "• Review and optimize current usage\n"
        body += "• Consider increasing budget limits\n"
        body += "• Contact support if assistance is needed\n"
        
        return body
    
    def get_configured_channels(self) -> List[str]:
        """Get list of configured notification channels"""
        channels = []
        
        if any([settings.SMTP_SERVER, settings.SMTP_USER, settings.SMTP_PASS]):
            channels.append("email")
        if settings.SLACK_WEBHOOK_URL:
            channels.append("slack")
        if settings.DISCORD_WEBHOOK_URL:
            channels.append("discord")
        if settings.TEAMS_WEBHOOK_URL:
            channels.append("teams")
        if settings.CUSTOM_WEBHOOK_URL:
            channels.append("webhook")
        
        return channels
    
    async def test_notifications(self) -> Dict[str, bool]:
        """Test all configured notification channels"""
        test_title = "🧪 Test Notification - Collexa Billing System"
        test_message = "This is a test notification to verify your alert channels are working correctly."
        
        success = self.apobj.notify(title=test_title, body=test_message)
        
        return {
            "success": success,
            "channels_configured": len(self.get_configured_channels()),
            "channels": self.get_configured_channels(),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global alert service instance
alert_service = AlertService()
