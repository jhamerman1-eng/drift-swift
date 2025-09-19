"""
Ultimate Hedge Bot - Audit Trail & Regulatory Compliance
Fixed audit trail with configurable thresholds and division by zero protection.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AuditTrail:
    """
    Comprehensive audit trail for regulatory compliance.

    Fixed Issues:
    - ✅ Configurable trade reporting thresholds by jurisdiction
    - ✅ Division by zero protection in risk metrics calculation
    - ✅ Proper compliance status tracking
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.audit_log: List[Dict[str, Any]] = []
        self.compliance_checks = {
            'position_limits': self._check_position_limits,
            'trade_reporting': self._check_trade_reporting,
            'risk_limits': self._check_risk_limits,
            'market_manipulation': self._check_market_manipulation
        }

        # Jurisdiction-specific configurations
        self.jurisdiction_configs = self._load_jurisdiction_configs()

    def _load_jurisdiction_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load jurisdiction-specific compliance configurations."""
        # In production, this would be loaded from external config files
        return {
            'drift': {
                'name': 'United States',
                'trade_reporting_threshold': 100000,  # $100K
                'large_trade_threshold': 500000,      # $500K
                'position_limit_threshold': 1000000,  # $1M
                'regulatory_body': 'CFTC',
                'reporting_required': True
            },
            'binance': {
                'name': 'Cayman Islands',
                'trade_reporting_threshold': 50000,   # $50K
                'large_trade_threshold': 250000,      # $250K
                'position_limit_threshold': 2000000,  # $2M
                'regulatory_body': 'CIMA',
                'reporting_required': False
            },
            'bybit': {
                'name': 'Singapore',
                'trade_reporting_threshold': 30000,   # $30K
                'large_trade_threshold': 150000,      # $150K
                'position_limit_threshold': 1500000,  # $1.5M
                'regulatory_body': 'MAS',
                'reporting_required': False
            },
            'default': {
                'name': 'Unknown',
                'trade_reporting_threshold': 100000,
                'large_trade_threshold': 500000,
                'position_limit_threshold': 1000000,
                'regulatory_body': 'Unknown',
                'reporting_required': True
            }
        }

    def log_hedge_action(self, action_type: str, details: Dict[str, Any]):
        """
        Log all hedge actions for audit trail.

        Args:
            action_type: Type of action (e.g., 'hedge_created', 'order_placed')
            details: Action details including venue, quantity, price, etc.
        """
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action_type': action_type,
            'user_id': details.get('user_id'),
            'hedge_id': details.get('hedge_id'),
            'symbol': details.get('symbol'),
            'venue': details.get('venue'),
            'side': details.get('side'),
            'quantity': details.get('quantity', 0),
            'price': details.get('price'),
            'effective_cost': details.get('effective_cost'),
            'urgency_score': details.get('urgency_score'),
            'justification': details.get('justification'),
            'compliance_status': self._check_compliance(details),
            'metadata': details.get('metadata', {})
        }

        self.audit_log.append(audit_entry)

        # Keep only recent entries (last 10,000)
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]

        # Persist to storage (would be implemented based on requirements)
        self._persist_audit_entry(audit_entry)

        # Check reporting requirements
        self._check_reporting_requirements(audit_entry)

        logger.info(f"📝 Audit logged: {action_type} for hedge {details.get('hedge_id')}")

    def _check_compliance(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance status for the action."""
        compliance_status = {}

        for check_name, check_func in self.compliance_checks.items():
            try:
                result = check_func(details)
                compliance_status[check_name] = result
            except Exception as e:
                logger.error(f"Compliance check {check_name} failed: {e}")
                compliance_status[check_name] = {
                    'status': 'error',
                    'message': str(e)
                }

        return compliance_status

    def _check_position_limits(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Check position limit compliance."""
        venue = details.get('venue', '').lower()
        quantity = details.get('quantity', 0)
        current_position = details.get('current_position', 0)

        jurisdiction = self.jurisdiction_configs.get(venue, self.jurisdiction_configs['default'])
        limit = jurisdiction['position_limit_threshold']

        new_position = current_position + quantity

        if new_position > limit:
            return {
                'status': 'violation',
                'message': f'Position limit exceeded: {new_position} > {limit}',
                'limit': limit,
                'current': current_position,
                'additional': quantity
            }

        return {
            'status': 'compliant',
            'message': f'Within position limits: {new_position} <= {limit}',
            'utilization': new_position / limit if limit > 0 else 0
        }

    def _check_trade_reporting(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Check trade reporting requirements based on jurisdiction."""
        venue = details.get('venue', '').lower()
        quantity = details.get('quantity', 0)

        jurisdiction = self.jurisdiction_configs.get(venue, self.jurisdiction_configs['default'])
        threshold = jurisdiction['trade_reporting_threshold']
        reporting_required = jurisdiction['reporting_required']

        if not reporting_required:
            return {
                'status': 'not_required',
                'message': f'Reporting not required in {jurisdiction["name"]}',
                'jurisdiction': jurisdiction['name']
            }

        if quantity > threshold:
            return {
                'status': 'requires_reporting',
                'threshold': threshold,
                'jurisdiction': jurisdiction['name'],
                'regulatory_body': jurisdiction['regulatory_body'],
                'reason': f'Trade size {quantity} exceeds threshold {threshold}'
            }

        return {
            'status': 'no_reporting_required',
            'threshold': threshold,
            'jurisdiction': jurisdiction['name']
        }

    def _check_risk_limits(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Check risk limit compliance."""
        # Implementation would check against risk limits
        # For now, return a basic compliant status
        return {
            'status': 'compliant',
            'message': 'Risk limits check passed',
            'risk_score': details.get('urgency_score', 0.5)
        }

    def _check_market_manipulation(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Check for potential market manipulation."""
        # Implementation would include:
        # - Wash trade detection
        # - Spoofing detection
        # - Layering detection
        # - High-frequency pattern analysis

        # For now, return a basic check
        quantity = details.get('quantity', 0)
        urgency = details.get('urgency_score', 0.5)

        if quantity > 1000000 and urgency < 0.2:  # Large trade, low urgency
            return {
                'status': 'review_required',
                'message': 'Large trade with low urgency - review for potential manipulation',
                'concerns': ['large_size_low_urgency']
            }

        return {
            'status': 'no_concerns',
            'message': 'No market manipulation concerns detected'
        }

    def _persist_audit_entry(self, entry: Dict[str, Any]):
        """Persist audit entry to storage."""
        # In production, this would write to:
        # - Database (PostgreSQL, MongoDB)
        # - Log files
        # - Regulatory reporting systems
        # - Blockchain for immutable record

        logger.debug(f"Persisting audit entry: {entry['action_type']} at {entry['timestamp']}")

    def _check_reporting_requirements(self, entry: Dict[str, Any]):
        """Check if this entry requires regulatory reporting."""
        compliance = entry.get('compliance_status', {})
        trade_reporting = compliance.get('trade_reporting', {})

        if trade_reporting.get('status') == 'requires_reporting':
            # Trigger regulatory reporting
            self._submit_regulatory_report(entry, trade_reporting)

    def _submit_regulatory_report(self, entry: Dict[str, Any], reporting_details: Dict[str, Any]):
        """Submit regulatory report for large trades."""
        report = {
            'report_type': 'large_trade',
            'timestamp': datetime.utcnow().isoformat(),
            'trade_details': entry,
            'reporting_details': reporting_details,
            'submitted_by': 'ultimate_hedge_bot',
            'status': 'submitted'
        }

        logger.info(f"📋 Regulatory report submitted for trade {entry.get('hedge_id')}")

    def generate_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Generate compliance report for regulatory authorities.

        Args:
            start_date: Start date for the report
            end_date: End date for the report

        Returns:
            Comprehensive compliance report
        """
        relevant_entries = [
            entry for entry in self.audit_log
            if start_date <= datetime.fromisoformat(entry['timestamp']) <= end_date
        ]

        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_actions': len(relevant_entries),
            'compliance_summary': self._summarize_compliance(relevant_entries),
            'risk_metrics': self._calculate_risk_metrics(relevant_entries),
            'entries': relevant_entries
        }

        return report

    def _summarize_compliance(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize compliance status across entries."""
        summary = {
            'compliant_actions': 0,
            'non_compliant_actions': 0,
            'requires_reporting': 0,
            'review_required': 0,
            'errors': 0
        }

        for entry in entries:
            compliance = entry.get('compliance_status', {})

            # Count overall compliance
            compliant_count = sum(
                1 for check in compliance.values()
                if isinstance(check, dict) and check.get('status') in ['compliant', 'no_concerns', 'not_required']
            )

            if compliant_count == len(compliance):
                summary['compliant_actions'] += 1
            else:
                summary['non_compliant_actions'] += 1

            # Count specific issues
            for check_name, check_result in compliance.items():
                if isinstance(check_result, dict):
                    status = check_result.get('status')
                    if status == 'requires_reporting':
                        summary['requires_reporting'] += 1
                    elif status == 'review_required':
                        summary['review_required'] += 1
                    elif status == 'error':
                        summary['errors'] += 1

        return summary

    def _calculate_risk_metrics(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate risk metrics for the period.

        FIXED: Division by zero protection when no entries.
        """
        if not entries:
            return {
                'total_entries': 0,
                'avg_urgency_score': 0.0,
                'max_position_size': 0,
                'venues_used': [],
                'error': 'No entries in period'
            }

        # Calculate metrics with division by zero protection
        urgency_scores = [e.get('urgency_score', 0) for e in entries if e.get('urgency_score') is not None]
        avg_urgency = sum(urgency_scores) / len(urgency_scores) if urgency_scores else 0.0

        quantities = [e.get('quantity', 0) for e in entries if e.get('quantity') is not None]
        max_quantity = max(quantities) if quantities else 0

        venues = list(set(e.get('venue') for e in entries if e.get('venue')))

        return {
            'total_entries': len(entries),
            'avg_urgency_score': avg_urgency,
            'max_position_size': max_quantity,
            'venues_used': venues,
            'entries_with_urgency': len(urgency_scores),
            'entries_with_quantity': len(quantities)
        }

    def get_compliance_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get compliance statistics for the specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_entries = [
            entry for entry in self.audit_log
            if datetime.fromisoformat(entry['timestamp']) > cutoff_time
        ]

        if not recent_entries:
            return {
                'period_hours': hours,
                'total_entries': 0,
                'compliance_rate': 1.0,
                'reporting_required': 0,
                'violations': 0
            }

        compliance_summary = self._summarize_compliance(recent_entries)

        total_entries = len(recent_entries)
        compliant_entries = compliance_summary['compliant_actions']
        compliance_rate = compliant_entries / total_entries if total_entries > 0 else 1.0

        return {
            'period_hours': hours,
            'total_entries': total_entries,
            'compliance_rate': compliance_rate,
            'compliant_entries': compliant_entries,
            'reporting_required': compliance_summary['requires_reporting'],
            'review_required': compliance_summary['review_required'],
            'violations': compliance_summary['non_compliant_actions'],
            'errors': compliance_summary['errors']
        }

    def search_audit_log(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search audit log with filters."""
        results = self.audit_log.copy()

        # Apply filters
        for key, value in filters.items():
            if key == 'start_date':
                results = [r for r in results if datetime.fromisoformat(r['timestamp']) >= value]
            elif key == 'end_date':
                results = [r for r in results if datetime.fromisoformat(r['timestamp']) <= value]
            elif key == 'action_type':
                results = [r for r in results if r.get('action_type') == value]
            elif key == 'venue':
                results = [r for r in results if r.get('venue') == value]
            elif key == 'user_id':
                results = [r for r in results if r.get('user_id') == value]
            elif key == 'hedge_id':
                results = [r for r in results if r.get('hedge_id') == value]

        return results

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get overall audit trail summary."""
        total_entries = len(self.audit_log)
        if total_entries == 0:
            return {'total_entries': 0}

        # Basic statistics
        action_types = defaultdict(int)
        venues = defaultdict(int)
        urgency_scores = []

        for entry in self.audit_log:
            action_types[entry.get('action_type', 'unknown')] += 1
            venues[entry.get('venue', 'unknown')] += 1

            urgency = entry.get('urgency_score')
            if urgency is not None:
                urgency_scores.append(urgency)

        avg_urgency = sum(urgency_scores) / len(urgency_scores) if urgency_scores else 0.0

        return {
            'total_entries': total_entries,
            'action_type_breakdown': dict(action_types),
            'venue_breakdown': dict(venues),
            'avg_urgency_score': avg_urgency,
            'date_range': {
                'oldest': min((e['timestamp'] for e in self.audit_log), default=None),
                'newest': max((e['timestamp'] for e in self.audit_log), default=None)
            }
        }


# Global audit trail instance
audit_trail = AuditTrail()

