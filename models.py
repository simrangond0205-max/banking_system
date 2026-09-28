from __future__ import annotations

import hashlib
import random
import string
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from constants import (
    CREDIT_CARD_ANNUAL_FEE,
    CREDIT_CARD_MIN_PAYMENT_PERCENT,
    MINIMUM_BALANCE_CURRENT,
    MINIMUM_BALANCE_SALARY,
    MINIMUM_BALANCE_SAVINGS,
    OVERDRAFT_FEE,
)


class AccountType(str, Enum):
    SAVINGS = "Savings"
    CURRENT = "Current"
    SALARY = "Salary"


def minimum_balance_for(account_type: AccountType) -> float:
    mapping = {
        AccountType.SAVINGS: MINIMUM_BALANCE_SAVINGS,
        AccountType.CURRENT: MINIMUM_BALANCE_CURRENT,
        AccountType.SALARY: MINIMUM_BALANCE_SALARY,
    }
    return mapping[account_type]


def _gen_id(prefix: str, length: int = 10) -> str:
    digits = "".join(random.choices(string.digits, k=length))
    return f"{prefix}{digits}"


def hash_pin(pin: str) -> str:
    if len(pin) != 4 or not pin.isdigit():
        raise ValueError("PIN must be exactly 4 digits.")
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


@dataclass
class Customer:
    customer_id: str
    name: str
    email: str
    phone: str


@dataclass
class BankAccount:
    account_number: str
    customer_id: str
    account_type: AccountType
    balance: float
    transactions: list[str] = field(default_factory=list)

    @classmethod
    def open_account(
        cls,
        customer_id: str,
        account_type: AccountType,
        initial_deposit: float,
    ) -> BankAccount:
        min_bal = minimum_balance_for(account_type)
        if initial_deposit < min_bal:
            raise ValueError(
                f"Initial deposit must be at least {min_bal:.2f} for {account_type.value}."
            )
        acct = cls(
            account_number=_gen_id("ACC"),
            customer_id=customer_id,
            account_type=account_type,
            balance=initial_deposit,
        )
        acct._log(f"Account opened with deposit {initial_deposit:.2f}")
        return acct

    def minimum_balance(self) -> float:
        return minimum_balance_for(self.account_type)

    def _log(self, message: str) -> None:
        self.transactions.append(f"{date.today().isoformat()} | {message}")

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance += amount
        self._log(f"Deposit +{amount:.2f} | Balance: {self.balance:.2f}")

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if self.balance - amount < self.minimum_balance():
            raise ValueError(
                f"Withdrawal would breach minimum balance "
                f"({self.minimum_balance():.2f}). Available above minimum: "
                f"{max(0.0, self.balance - self.minimum_balance()):.2f}"
            )
        self.balance -= amount
        self._log(f"Withdrawal -{amount:.2f} | Balance: {self.balance:.2f}")

    def debit_withdraw(self, amount: float, card_number: str) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if self.balance - amount < self.minimum_balance():
            raise ValueError(
                f"Withdrawal would breach minimum balance "
                f"({self.minimum_balance():.2f}). Available above minimum: "
                f"{max(0.0, self.balance - self.minimum_balance()):.2f}"
            )
        self.balance -= amount
        self._log(
            f"Debit card {card_number} purchase -{amount:.2f} | Balance: {self.balance:.2f}"
        )

    def summary(self) -> str:
        return (
            f"{self.account_number} ({self.account_type.value}) | "
            f"Balance: {self.balance:.2f} | Min required: {self.minimum_balance():.2f}"
        )


@dataclass
class DebitCard:
    card_number: str
    account_number: str
    daily_limit: float
    pin_hash: str
    is_active: bool = True
    spent_today: float = 0.0
    spent_date: str = ""

    @classmethod
    def issue(cls, account_number: str, pin: str, daily_limit: float = 50_000.0) -> DebitCard:
        return cls(
            card_number=_gen_id("DC", 12),
            account_number=account_number,
            daily_limit=daily_limit,
            pin_hash=hash_pin(pin),
            spent_date=date.today().isoformat(),
        )

    def verify_pin(self, pin: str) -> bool:
        try:
            return hash_pin(pin) == self.pin_hash
        except ValueError:
            return False

    def _reset_daily_limit_if_needed(self) -> None:
        today = date.today().isoformat()
        if self.spent_date != today:
            self.spent_date = today
            self.spent_today = 0.0

    def purchase(self, account: BankAccount, pin: str, amount: float) -> None:
        if not self.is_active:
            raise ValueError("Debit card is blocked.")
        if not self.verify_pin(pin):
            raise ValueError("Incorrect PIN.")
        if amount <= 0:
            raise ValueError("Purchase amount must be positive.")
        self._reset_daily_limit_if_needed()
        if self.spent_today + amount > self.daily_limit:
            raise ValueError(
                f"Daily limit exceeded. Remaining today: "
                f"{max(0.0, self.daily_limit - self.spent_today):.2f}"
            )
        account.debit_withdraw(amount, self.card_number)
        self.spent_today += amount


@dataclass
class CreditCard:
    card_number: str
    customer_id: str
    credit_limit: float
    outstanding: float = 0.0
    is_active: bool = True

    @classmethod
    def issue(cls, customer_id: str, credit_limit: float) -> CreditCard:
        return cls(
            card_number=_gen_id("CC", 12),
            customer_id=customer_id,
            credit_limit=credit_limit,
            outstanding=CREDIT_CARD_ANNUAL_FEE,
        )

    def available_credit(self) -> float:
        return max(0.0, self.credit_limit - self.outstanding)

    def swipe(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Purchase amount must be positive.")
        if amount > self.available_credit():
            raise ValueError("Insufficient credit limit.")
        self.outstanding += amount

    def pay(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Payment must be positive.")
        self.outstanding = max(0.0, self.outstanding - amount)

    def minimum_due(self) -> float:
        return round(self.outstanding * (CREDIT_CARD_MIN_PAYMENT_PERCENT / 100), 2)

    def summary(self) -> str:
        return (
            f"{self.card_number} | Limit: {self.credit_limit:.2f} | "
            f"Outstanding: {self.outstanding:.2f} | Min due: {self.minimum_due():.2f}"
        )


@dataclass
class SupportTicket:
    ticket_id: str
    customer_id: str
    category: str
    subject: str
    status: str = "Open"

    @classmethod
    def create(cls, customer_id: str, category: str, subject: str) -> SupportTicket:
        return cls(
            ticket_id=_gen_id("TKT"),
            customer_id=customer_id,
            category=category,
            subject=subject,
        )
