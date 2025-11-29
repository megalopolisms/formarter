"""
Docket Analyzer Module - Federal Pro Se Litigation Support
Ported from the docket-parser agent for use in Formarter and Claude CLI

Features:
- Motion pattern recognition
- Rule 6(d) deadline calculations with pro se adjustments
- Motion chain linking (motions → responses → replies → orders)
- Entry classification
- Critical deadline alerts
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class EntryType(Enum):
    MOTION = "MOTION"
    RESPONSE = "RESPONSE"
    REPLY = "REPLY"
    ORDER = "ORDER"
    COMPLAINT = "COMPLAINT"
    ANSWER = "ANSWER"
    NOTICE = "NOTICE"
    SUMMONS = "SUMMONS"
    OTHER = "OTHER"


class MotionType(Enum):
    DISMISS = "Motion to Dismiss"
    TRO = "Motion for TRO"
    INJUNCTION = "Motion for Injunction"
    SANCTIONS = "Motion for Sanctions"
    DISQUALIFY = "Motion to Disqualify Counsel"
    CONSOLIDATE = "Motion to Consolidate"
    STRIKE = "Motion to Strike"
    EXTENSION = "Motion for Extension of Time"
    SUBSTITUTE = "Motion to Substitute Party"
    AMEND = "Motion to Amend"
    RECONSIDERATION = "Motion to Reconsider"
    SUMMARY_JUDGMENT = "Motion for Summary Judgment"
    PROTECTIVE_ORDER = "Motion for Protective Order"
    COMPEL = "Motion to Compel"
    OTHER = "Other Motion"


class OrderStatus(Enum):
    GRANTED = "Granted"
    DENIED = "Denied"
    WITHDRAWN = "Withdrawn"
    STRICKEN = "Stricken"
    MOOT = "Moot"
    PENDING = "Pending"


@dataclass
class DeadlineInfo:
    """Represents a calculated deadline"""
    deadline_date: datetime
    base_days: int
    pro_se_adjustment: int
    total_days: int
    description: str
    is_jurisdictional: bool = False
    source_entry: Optional[int] = None


@dataclass
class MotionChain:
    """Represents a motion and its related responses/orders"""
    motion_docket_num: int
    motion_type: MotionType
    motion_date: datetime
    motion_text: str
    filed_by: str
    responses: List[int] = field(default_factory=list)
    replies: List[int] = field(default_factory=list)
    orders: List[int] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    response_deadline: Optional[DeadlineInfo] = None
    reply_deadline: Optional[DeadlineInfo] = None


class DocketAnalyzer:
    """
    Federal docket analyzer with pro se deadline calculations
    and motion pattern recognition
    """

    # Motion patterns (regex)
    MOTION_PATTERNS = {
        MotionType.DISMISS: re.compile(r'MOTION\s+to\s+Dismiss(?:\s+(?:for\s+)?(.+?))?', re.I),
        MotionType.TRO: re.compile(r'MOTION\s+for\s+(?:Temporary\s+Restraining\s+Order|TRO)', re.I),
        MotionType.INJUNCTION: re.compile(r'MOTION\s+for\s+(?:Preliminary\s+)?Injunction', re.I),
        MotionType.SANCTIONS: re.compile(r'MOTION\s+for\s+(?:Rule\s+11\s+)?Sanctions', re.I),
        MotionType.DISQUALIFY: re.compile(r'MOTION\s+to\s+Disqualify\s+Counsel', re.I),
        MotionType.CONSOLIDATE: re.compile(r'MOTION\s+to\s+Consolidate', re.I),
        MotionType.STRIKE: re.compile(r'MOTION\s+to\s+Strike', re.I),
        MotionType.EXTENSION: re.compile(r'MOTION\s+for\s+Extension\s+of\s+Time', re.I),
        MotionType.SUBSTITUTE: re.compile(r'MOTION\s+to\s+Substitute\s+Party', re.I),
        MotionType.AMEND: re.compile(r'MOTION\s+(?:for\s+leave\s+to\s+file\s+)?(?:to\s+)?[Aa]mend', re.I),
        MotionType.RECONSIDERATION: re.compile(r'MOTION\s+to\s+(?:Alter\s+or\s+Amend|Reconsider)', re.I),
        MotionType.SUMMARY_JUDGMENT: re.compile(r'MOTION\s+for\s+Summary\s+Judgment', re.I),
        MotionType.PROTECTIVE_ORDER: re.compile(r'MOTION\s+for\s+Protective\s+Order', re.I),
        MotionType.COMPEL: re.compile(r'MOTION\s+to\s+Compel', re.I),
    }

    # Response patterns
    RESPONSE_PATTERNS = {
        'response': re.compile(r'RESPONSE\s+(?:in\s+)?Opposition\s+(?:re\s+|to\s+)?(\d+)', re.I),
        'reply': re.compile(r'REPL?Y\s+(?:in\s+Support\s+)?(?:re\s+|to\s+)?(\d+)', re.I),
        'joinder': re.compile(r'(?:JOINDER|joining)\s+(?:in\s+)?(?:re\s+|to\s+)?(\d+)', re.I),
        'supplement': re.compile(r'SUPPLEMENT(?:AL)?\s+(?:re\s+|to\s+)?(\d+)', re.I),
    }

    # Order patterns
    ORDER_PATTERNS = {
        OrderStatus.GRANTED: re.compile(r'(?:TEXT\s+)?(?:ONL?Y\s+)?ORDER\s+granting\s+(\d+)', re.I),
        OrderStatus.DENIED: re.compile(r'(?:TEXT\s+)?(?:ONL?Y\s+)?ORDER\s+denying\s+(\d+)', re.I),
        OrderStatus.WITHDRAWN: re.compile(r'(?:ORDER\s+)?(?:withdrawing|WITHDRAWN)\s+(\d+)', re.I),
        OrderStatus.STRICKEN: re.compile(r'(?:ORDER\s+)?(?:striking|STRICKEN)\s+(\d+)', re.I),
        OrderStatus.MOOT: re.compile(r'(?:ORDER\s+)?.*moot.*(\d+)', re.I),
    }

    # Emergency indicators
    EMERGENCY_PATTERNS = [
        re.compile(r'EMERGENCY', re.I),
        re.compile(r'EX\s+PARTE', re.I),
        re.compile(r'URGENT', re.I),
        re.compile(r'NECESSITOUS', re.I),
        re.compile(r'IMMEDIATE', re.I),
    ]

    # Federal deadline rules (in days)
    # Pro se litigants get +3 days for electronic/mail service under Rule 6(d)
    DEADLINE_RULES = {
        'motion_response': {'base': 14, 'pro_se_adj': 3, 'jurisdictional': False},
        'motion_reply': {'base': 7, 'pro_se_adj': 3, 'jurisdictional': False},
        'appeal': {'base': 30, 'pro_se_adj': 3, 'jurisdictional': True},  # 60 if US is party
        'objection_magistrate': {'base': 14, 'pro_se_adj': 3, 'jurisdictional': False},
        'rule_59_motion': {'base': 28, 'pro_se_adj': 0, 'jurisdictional': True},
        'rule_60_motion': {'base': 365, 'pro_se_adj': 0, 'jurisdictional': True},
        'discovery_response': {'base': 30, 'pro_se_adj': 3, 'jurisdictional': False},
        'service_complaint': {'base': 90, 'pro_se_adj': 0, 'jurisdictional': True},
        'answer': {'base': 21, 'pro_se_adj': 3, 'jurisdictional': False},
    }

    def __init__(self, is_pro_se: bool = True):
        """
        Initialize the docket analyzer

        Args:
            is_pro_se: Whether the plaintiff is pro se (affects deadline calculations)
        """
        self.is_pro_se = is_pro_se
        self.motion_chains: Dict[int, MotionChain] = {}

    def classify_entry(self, text: str) -> Tuple[EntryType, Optional[MotionType]]:
        """
        Classify a docket entry by type

        Returns:
            Tuple of (EntryType, MotionType if applicable)
        """
        text_upper = text.upper()

        # Check for motions first
        for motion_type, pattern in self.MOTION_PATTERNS.items():
            if pattern.search(text):
                return EntryType.MOTION, motion_type

        # Generic motion check
        if 'MOTION' in text_upper:
            return EntryType.MOTION, MotionType.OTHER

        # Check for responses
        for resp_type, pattern in self.RESPONSE_PATTERNS.items():
            if pattern.search(text):
                if resp_type == 'reply':
                    return EntryType.REPLY, None
                return EntryType.RESPONSE, None

        # Check for orders
        for status, pattern in self.ORDER_PATTERNS.items():
            if pattern.search(text):
                return EntryType.ORDER, None

        # Other classifications
        if 'ORDER' in text_upper:
            return EntryType.ORDER, None
        if 'COMPLAINT' in text_upper or 'AMENDED COMPLAINT' in text_upper:
            return EntryType.COMPLAINT, None
        if 'ANSWER' in text_upper:
            return EntryType.ANSWER, None
        if 'NOTICE' in text_upper:
            return EntryType.NOTICE, None
        if 'SUMMONS' in text_upper:
            return EntryType.SUMMONS, None

        return EntryType.OTHER, None

    def is_emergency(self, text: str) -> bool:
        """Check if entry indicates an emergency motion"""
        for pattern in self.EMERGENCY_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def calculate_deadline(self, from_date: datetime, deadline_type: str) -> DeadlineInfo:
        """
        Calculate a deadline with pro se adjustments

        Args:
            from_date: The date the deadline starts from
            deadline_type: Type of deadline (from DEADLINE_RULES keys)

        Returns:
            DeadlineInfo with calculated deadline
        """
        if deadline_type not in self.DEADLINE_RULES:
            raise ValueError(f"Unknown deadline type: {deadline_type}")

        rule = self.DEADLINE_RULES[deadline_type]
        base_days = rule['base']
        pro_se_adj = rule['pro_se_adj'] if self.is_pro_se else 0
        total_days = base_days + pro_se_adj

        deadline_date = from_date + timedelta(days=total_days)

        # Adjust for weekends (if deadline falls on weekend, move to Monday)
        if deadline_date.weekday() == 5:  # Saturday
            deadline_date += timedelta(days=2)
        elif deadline_date.weekday() == 6:  # Sunday
            deadline_date += timedelta(days=1)

        return DeadlineInfo(
            deadline_date=deadline_date,
            base_days=base_days,
            pro_se_adjustment=pro_se_adj,
            total_days=total_days,
            description=f"{deadline_type.replace('_', ' ').title()}",
            is_jurisdictional=rule['jurisdictional']
        )

    def extract_related_docket_num(self, text: str) -> Optional[int]:
        """Extract referenced docket number from text (e.g., 're 10 MOTION')"""
        # Pattern for "re X" or "to X" references
        patterns = [
            re.compile(r're\s+(\d+)', re.I),
            re.compile(r'to\s+(\d+)\s+MOTION', re.I),
            re.compile(r'#\s*(\d+)', re.I),
        ]

        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        return None

    def analyze_entries(self, entries: List[dict]) -> Dict:
        """
        Analyze a list of docket entries

        Args:
            entries: List of docket entry dicts with keys:
                     docket_number, date, text, filed_by (optional)

        Returns:
            Analysis results including motion chains, deadlines, alerts
        """
        self.motion_chains = {}
        classified_entries = []

        # First pass: classify all entries
        for entry in entries:
            entry_type, motion_type = self.classify_entry(entry.get('text', ''))
            is_emergency = self.is_emergency(entry.get('text', ''))

            classified = {
                **entry,
                'entry_type': entry_type,
                'motion_type': motion_type,
                'is_emergency': is_emergency,
                'related_to': self.extract_related_docket_num(entry.get('text', ''))
            }
            classified_entries.append(classified)

            # Build motion chains
            if entry_type == EntryType.MOTION:
                docket_num = entry.get('docket_number')
                date_str = entry.get('date')
                date = datetime.strptime(date_str, '%Y-%m-%d') if isinstance(date_str, str) else date_str

                self.motion_chains[docket_num] = MotionChain(
                    motion_docket_num=docket_num,
                    motion_type=motion_type or MotionType.OTHER,
                    motion_date=date,
                    motion_text=entry.get('text', ''),
                    filed_by=entry.get('filed_by', 'Unknown'),
                    response_deadline=self.calculate_deadline(date, 'motion_response'),
                    reply_deadline=None  # Calculated after response
                )

        # Second pass: link responses and orders to motions
        for entry in classified_entries:
            related_to = entry.get('related_to')
            if related_to and related_to in self.motion_chains:
                chain = self.motion_chains[related_to]
                docket_num = entry.get('docket_number')

                if entry['entry_type'] == EntryType.RESPONSE:
                    chain.responses.append(docket_num)
                    # Calculate reply deadline from response date
                    date_str = entry.get('date')
                    date = datetime.strptime(date_str, '%Y-%m-%d') if isinstance(date_str, str) else date_str
                    chain.reply_deadline = self.calculate_deadline(date, 'motion_reply')

                elif entry['entry_type'] == EntryType.REPLY:
                    chain.replies.append(docket_num)

                elif entry['entry_type'] == EntryType.ORDER:
                    chain.orders.append(docket_num)
                    # Update status based on order
                    for status, pattern in self.ORDER_PATTERNS.items():
                        if pattern.search(entry.get('text', '')):
                            chain.status = status
                            break

        # Generate alerts for upcoming deadlines
        alerts = self._generate_alerts()

        return {
            'classified_entries': classified_entries,
            'motion_chains': self.motion_chains,
            'alerts': alerts,
            'summary': self._generate_summary(classified_entries)
        }

    def _generate_alerts(self) -> List[dict]:
        """Generate alerts for upcoming/overdue deadlines"""
        alerts = []
        today = datetime.now()

        for docket_num, chain in self.motion_chains.items():
            if chain.status != OrderStatus.PENDING:
                continue  # Motion already resolved

            # Check response deadline
            if chain.response_deadline and not chain.responses:
                deadline = chain.response_deadline.deadline_date
                days_until = (deadline - today).days

                if days_until < 0:
                    alerts.append({
                        'type': 'OVERDUE',
                        'priority': 'CRITICAL',
                        'motion_docket': docket_num,
                        'motion_type': chain.motion_type.value,
                        'deadline_type': 'Response',
                        'deadline_date': deadline.strftime('%Y-%m-%d'),
                        'days_overdue': abs(days_until),
                        'message': f"OVERDUE: Response to {chain.motion_type.value} (#{docket_num}) was due {abs(days_until)} days ago!"
                    })
                elif days_until <= 7:
                    alerts.append({
                        'type': 'UPCOMING',
                        'priority': 'HIGH' if days_until <= 3 else 'MEDIUM',
                        'motion_docket': docket_num,
                        'motion_type': chain.motion_type.value,
                        'deadline_type': 'Response',
                        'deadline_date': deadline.strftime('%Y-%m-%d'),
                        'days_remaining': days_until,
                        'message': f"Response to {chain.motion_type.value} (#{docket_num}) due in {days_until} days"
                    })

            # Check reply deadline if response was filed
            if chain.reply_deadline and chain.responses and not chain.replies:
                deadline = chain.reply_deadline.deadline_date
                days_until = (deadline - today).days

                if days_until < 0:
                    alerts.append({
                        'type': 'OVERDUE',
                        'priority': 'HIGH',
                        'motion_docket': docket_num,
                        'motion_type': chain.motion_type.value,
                        'deadline_type': 'Reply',
                        'deadline_date': deadline.strftime('%Y-%m-%d'),
                        'days_overdue': abs(days_until),
                        'message': f"OVERDUE: Reply for {chain.motion_type.value} (#{docket_num}) was due {abs(days_until)} days ago"
                    })
                elif days_until <= 5:
                    alerts.append({
                        'type': 'UPCOMING',
                        'priority': 'MEDIUM',
                        'motion_docket': docket_num,
                        'motion_type': chain.motion_type.value,
                        'deadline_type': 'Reply',
                        'deadline_date': deadline.strftime('%Y-%m-%d'),
                        'days_remaining': days_until,
                        'message': f"Reply for {chain.motion_type.value} (#{docket_num}) due in {days_until} days"
                    })

        # Sort by priority (CRITICAL first, then by days)
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        alerts.sort(key=lambda x: (priority_order.get(x['priority'], 4), x.get('days_remaining', x.get('days_overdue', 0))))

        return alerts

    def _generate_summary(self, entries: List[dict]) -> dict:
        """Generate summary statistics"""
        type_counts = {}
        for entry in entries:
            entry_type = entry['entry_type'].value
            type_counts[entry_type] = type_counts.get(entry_type, 0) + 1

        pending_motions = [c for c in self.motion_chains.values() if c.status == OrderStatus.PENDING]
        resolved_motions = [c for c in self.motion_chains.values() if c.status != OrderStatus.PENDING]

        return {
            'total_entries': len(entries),
            'entry_types': type_counts,
            'total_motions': len(self.motion_chains),
            'pending_motions': len(pending_motions),
            'resolved_motions': len(resolved_motions),
            'emergency_motions': sum(1 for e in entries if e.get('is_emergency', False))
        }

    def format_deadline_report(self) -> str:
        """Generate a formatted deadline report for CLI output"""
        lines = []
        lines.append("=" * 60)
        lines.append("FEDERAL LITIGATION DEADLINE REPORT")
        lines.append(f"Pro Se Status: {'YES (+3 days Rule 6(d))' if self.is_pro_se else 'NO'}")
        lines.append("=" * 60)

        alerts = self._generate_alerts()

        if not alerts:
            lines.append("\nNo pending deadlines.")
        else:
            # Critical/Overdue
            overdue = [a for a in alerts if a['type'] == 'OVERDUE']
            if overdue:
                lines.append("\n### OVERDUE DEADLINES ###")
                for alert in overdue:
                    lines.append(f"  [!] {alert['message']}")

            # Upcoming
            upcoming = [a for a in alerts if a['type'] == 'UPCOMING']
            if upcoming:
                lines.append("\n### UPCOMING DEADLINES ###")
                for alert in upcoming:
                    priority_marker = {'HIGH': '[!!]', 'MEDIUM': '[!]', 'LOW': '[-]'}.get(alert['priority'], '[-]')
                    lines.append(f"  {priority_marker} {alert['message']}")

        # Motion chains summary
        lines.append("\n" + "-" * 60)
        lines.append("MOTION STATUS SUMMARY")
        lines.append("-" * 60)

        for docket_num, chain in self.motion_chains.items():
            status_emoji = {
                OrderStatus.PENDING: "PENDING",
                OrderStatus.GRANTED: "GRANTED",
                OrderStatus.DENIED: "DENIED",
                OrderStatus.WITHDRAWN: "WITHDRAWN",
                OrderStatus.STRICKEN: "STRICKEN",
                OrderStatus.MOOT: "MOOT"
            }.get(chain.status, "?")

            lines.append(f"\n#{docket_num} - {chain.motion_type.value}")
            lines.append(f"   Filed: {chain.motion_date.strftime('%Y-%m-%d')} by {chain.filed_by}")
            lines.append(f"   Status: {status_emoji}")

            if chain.responses:
                lines.append(f"   Responses: #{', #'.join(map(str, chain.responses))}")
            if chain.replies:
                lines.append(f"   Replies: #{', #'.join(map(str, chain.replies))}")
            if chain.orders:
                lines.append(f"   Orders: #{', #'.join(map(str, chain.orders))}")

            if chain.status == OrderStatus.PENDING:
                if chain.response_deadline and not chain.responses:
                    dl = chain.response_deadline
                    lines.append(f"   Response Due: {dl.deadline_date.strftime('%Y-%m-%d')} ({dl.base_days}+{dl.pro_se_adjustment} days)")
                if chain.reply_deadline and chain.responses and not chain.replies:
                    dl = chain.reply_deadline
                    lines.append(f"   Reply Due: {dl.deadline_date.strftime('%Y-%m-%d')} ({dl.base_days}+{dl.pro_se_adjustment} days)")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


# CLI interface for Claude Code
def analyze_case_docket(case_number: str, entries: List[dict], is_pro_se: bool = True) -> str:
    """
    Analyze a case docket - callable from Claude CLI

    Args:
        case_number: The case number
        entries: List of docket entries
        is_pro_se: Whether plaintiff is pro se

    Returns:
        Formatted analysis report
    """
    analyzer = DocketAnalyzer(is_pro_se=is_pro_se)
    results = analyzer.analyze_entries(entries)

    report = []
    report.append(f"DOCKET ANALYSIS: Case {case_number}")
    report.append(analyzer.format_deadline_report())

    # Add summary
    summary = results['summary']
    report.append(f"\nSUMMARY:")
    report.append(f"  Total Entries: {summary['total_entries']}")
    report.append(f"  Total Motions: {summary['total_motions']}")
    report.append(f"  Pending: {summary['pending_motions']}")
    report.append(f"  Resolved: {summary['resolved_motions']}")

    return "\n".join(report)
