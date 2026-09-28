from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from constants import LOAN_TYPES


class LoanStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    ACTIVE = "Active"
    CLOSED = "Closed"
    REJECTED = "Rejected"


class LoanType(str, Enum):
    HOME = "Home Loan"
    PERSONAL = "Personal Loan"
    AUTO = "Auto / Vehicle Loan"
    EDUCATION = "Education Loan"
    BUSINESS = "Business Loan"
    GOLD = "Gold Loan"
    AGRICULTURE = "Agriculture Loan"


# Typical policy ranges (amounts in currency units)
LOAN_POLICY: dict[LoanType, dict[str, float]] = {
    LoanType.HOME: {"min_amount": 100_000, "max_amount": 5_000_000, "rate_percent": 8.5, "max_tenure_months": 360},
    LoanType.PERSONAL: {"min_amount": 10_000, "max_amount": 500_000, "rate_percent": 12.0, "max_tenure_months": 60},
    LoanType.AUTO: {"min_amount": 50_000, "max_amount": 2_000_000, "rate_percent": 9.5, "max_tenure_months": 84},
    LoanType.EDUCATION: {"min_amount": 25_000, "max_amount": 1_500_000, "rate_percent": 10.0, "max_tenure_months": 120},
    LoanType.BUSINESS: {"min_amount": 100_000, "max_amount": 10_000_000, "rate_percent": 11.5, "max_tenure_months": 120},
    LoanType.GOLD: {"min_amount": 5_000, "max_amount": 500_000, "rate_percent": 9.0, "max_tenure_months": 36},
    LoanType.AGRICULTURE: {"min_amount": 20_000, "max_amount": 2_000_000, "rate_percent": 7.5, "max_tenure_months": 60},
}


def list_loan_sections() -> list[str]:
    """All loan sections offered by the bank."""
    return list(LOAN_TYPES)


def _loan_id() -> str:
    return "LN" + "".join(random.choices(string.digits, k=8))


def _emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    if tenure_months <= 0:
        return 0.0
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return principal / tenure_months
    factor = (1 + monthly_rate) ** tenure_months
    return principal * monthly_rate * factor / (factor - 1)


@dataclass
class LoanApplication:
    loan_id: str
    customer_id: str
    loan_type: LoanType
    amount: float
    tenure_months: int
    status: LoanStatus = LoanStatus.PENDING
    emi: float = 0.0
    balance: float = 0.0
    payments: list[str] = field(default_factory=list)

    @classmethod
    def apply(
        cls,
        customer_id: str,
        loan_type: LoanType,
        amount: float,
        tenure_months: int,
    ) -> LoanApplication:
        policy = LOAN_POLICY[loan_type]
        if amount < policy["min_amount"] or amount > policy["max_amount"]:
            raise ValueError(
                f"{loan_type.value} amount must be between "
                f"{policy['min_amount']:.0f} and {policy['max_amount']:.0f}."
            )
        if tenure_months < 1 or tenure_months > policy["max_tenure_months"]:
            raise ValueError(
                f"Tenure must be 1–{int(policy['max_tenure_months'])} months for {loan_type.value}."
            )
        emi = round(_emi(amount, policy["rate_percent"], tenure_months), 2)
        return cls(
            loan_id=_loan_id(),
            customer_id=customer_id,
            loan_type=loan_type,
            amount=amount,
            tenure_months=tenure_months,
            emi=emi,
        )

    def approve(self) -> None:
        if self.status != LoanStatus.PENDING:
            raise ValueError("Only pending applications can be approved.")
        self.status = LoanStatus.APPROVED

    def disburse(self) -> None:
        if self.status != LoanStatus.APPROVED:
            raise ValueError("Loan must be approved before disbursement.")
        self.status = LoanStatus.ACTIVE
        self.balance = self.amount

    def pay_emi(self, amount: Optional[float] = None) -> None:
        if self.status != LoanStatus.ACTIVE:
            raise ValueError("EMI can only be paid on active loans.")
        pay = amount if amount is not None else self.emi
        if pay <= 0:
            raise ValueError("Payment must be positive.")
        self.balance = max(0.0, self.balance - pay)
        self.payments.append(f"{date.today().isoformat()} | EMI paid {pay:.2f}")
        if self.balance <= 0:
            self.status = LoanStatus.CLOSED
            self.balance = 0.0

    def policy_summary(self) -> str:
        p = LOAN_POLICY[self.loan_type]
        return (
            f"{self.loan_type.value} | Amount: {self.amount:.2f} | "
            f"Tenure: {self.tenure_months} mo | EMI: {self.emi:.2f} | "
            f"Rate: {p['rate_percent']}% | Status: {self.status.value} | "
            f"Balance: {self.balance:.2f}"
        )
