from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from models import SupportTicket


SERVICE_CATEGORIES = (
    "Account & Balance",
    "Debit Card",
    "Credit Card",
    "Loans",
    "Transactions & Disputes",
    "Branch & ATM",
    "General Inquiry",
)


@dataclass
class CustomerServiceDesk:
    tickets: list[SupportTicket] = field(default_factory=list)
    faq: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.faq:
            self.faq = {
                "minimum balance": (
                    "Savings: 500 | Current: 1000 | Salary: 0. "
                    "Withdrawals cannot reduce balance below these limits."
                ),
                "debit card": "Debit cards are linked to your account. Daily POS/ATM limit applies.",
                "credit card": "Pay at least 5% of outstanding balance as minimum due each cycle.",
                "loan types": (
                    "Home, Personal, Auto, Education, Business, Gold, and Agriculture loans are available."
                ),
            }

    def create_ticket(self, customer_id: str, category: str, subject: str) -> SupportTicket:
        if category not in SERVICE_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(SERVICE_CATEGORIES)}")
        ticket = SupportTicket.create(customer_id, category, subject)
        self.tickets.append(ticket)
        return ticket

    def resolve_ticket(self, ticket_id: str) -> None:
        for t in self.tickets:
            if t.ticket_id == ticket_id:
                t.status = "Resolved"
                return
        raise ValueError("Ticket not found.")

    def lookup_faq(self, keyword: str) -> Optional[str]:
        key = keyword.strip().lower()
        for topic, answer in self.faq.items():
            if key in topic or topic in key:
                return answer
        return None

    def contact_info(self) -> str:
        return (
            "Customer Service\n"
            "  Phone: 1800-000-BANK (24/7)\n"
            "  Email: help@mybank.example\n"
            "  Branch hours: Mon-Sat 10:00-16:00"
        )
