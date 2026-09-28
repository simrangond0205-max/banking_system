from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from customer_service import CustomerServiceDesk
from loans import LoanApplication, LoanType, list_loan_sections
from models import (
    AccountType,
    BankAccount,
    CreditCard,
    Customer,
    DebitCard,
    minimum_balance_for,
)

if TYPE_CHECKING:
    from storage import BankRepository


@dataclass
class BankingSystem:
    customers: dict[str, Customer] = field(default_factory=dict)
    accounts: dict[str, BankAccount] = field(default_factory=dict)
    debit_cards: dict[str, DebitCard] = field(default_factory=dict)
    credit_cards: dict[str, CreditCard] = field(default_factory=dict)
    loans: dict[str, LoanApplication] = field(default_factory=dict)
    service: CustomerServiceDesk = field(default_factory=CustomerServiceDesk)
    repository: Optional[BankRepository] = field(default=None, repr=False)
    _next_customer_seq: int = field(default=1, repr=False)

    def persist(self) -> None:
        if self.repository is not None:
            self.repository.save(self)

    def register_customer(self, name: str, email: str, phone: str) -> Customer:
        cid = f"CUST{self._next_customer_seq:04d}"
        self._next_customer_seq += 1
        customer = Customer(customer_id=cid, name=name, email=email, phone=phone)
        self.customers[cid] = customer
        self.persist()
        return customer

    def deposit(self, account_number: str, amount: float) -> None:
        self._require_account(account_number).deposit(amount)
        self.persist()

    def withdraw(self, account_number: str, amount: float) -> None:
        self._require_account(account_number).withdraw(amount)
        self.persist()

    def open_account(
        self,
        customer_id: str,
        account_type: AccountType,
        initial_deposit: float,
    ) -> BankAccount:
        self._require_customer(customer_id)
        account = BankAccount.open_account(customer_id, account_type, initial_deposit)
        self.accounts[account.account_number] = account
        self.persist()
        return account

    def issue_debit_card(self, account_number: str, pin: str) -> DebitCard:
        account = self._require_account(account_number)
        card = DebitCard.issue(account.account_number, pin)
        self.debit_cards[card.card_number] = card
        self.persist()
        return card

    def debit_purchase(self, card_number: str, pin: str, amount: float) -> None:
        card = self._require_debit_card(card_number)
        account = self._require_account(card.account_number)
        card.purchase(account, pin, amount)
        self.persist()

    def issue_credit_card(self, customer_id: str, credit_limit: float) -> CreditCard:
        self._require_customer(customer_id)
        if credit_limit < 5_000:
            raise ValueError("Minimum credit limit is 5000.")
        card = CreditCard.issue(customer_id, credit_limit)
        self.credit_cards[card.card_number] = card
        self.persist()
        return card

    def credit_purchase(self, card_number: str, amount: float) -> None:
        card = self._require_credit_card(card_number)
        if not card.is_active:
            raise ValueError("Credit card is blocked.")
        card.swipe(amount)
        self.persist()

    def pay_credit_card(self, card_number: str, amount: float) -> None:
        card = self._require_credit_card(card_number)
        card.pay(amount)
        self.persist()

    def apply_loan(
        self,
        customer_id: str,
        loan_type: LoanType,
        amount: float,
        tenure_months: int,
    ) -> LoanApplication:
        self._require_customer(customer_id)
        app = LoanApplication.apply(customer_id, loan_type, amount, tenure_months)
        self.loans[app.loan_id] = app
        self.persist()
        return app

    def approve_and_disburse_loan(self, loan_id: str, credit_account: str) -> None:
        loan = self._require_loan(loan_id)
        account = self._require_account(credit_account)
        if account.customer_id != loan.customer_id:
            raise ValueError("Loan disbursement account must belong to the same customer.")
        loan.approve()
        loan.disburse()
        account.deposit(loan.amount)
        self.persist()

    def pay_loan_emi(self, loan_id: str, amount: Optional[float] = None) -> None:
        loan = self._require_loan(loan_id)
        loan.pay_emi(amount)
        self.persist()

    def create_support_ticket(self, customer_id: str, category: str, subject: str):
        self._require_customer(customer_id)
        ticket = self.service.create_ticket(customer_id, category, subject)
        self.persist()
        return ticket

    def accounts_for_customer(self, customer_id: str) -> list[BankAccount]:
        return [a for a in self.accounts.values() if a.customer_id == customer_id]

    def loans_for_customer(self, customer_id: str) -> list[LoanApplication]:
        return [loan for loan in self.loans.values() if loan.customer_id == customer_id]

    def cards_for_customer(self, customer_id: str) -> tuple[list[DebitCard], list[CreditCard]]:
        account_nums = {a.account_number for a in self.accounts_for_customer(customer_id)}
        debit = [d for d in self.debit_cards.values() if d.account_number in account_nums]
        credit = [c for c in self.credit_cards.values() if c.customer_id == customer_id]
        return debit, credit

    def get_minimum_balances(self) -> dict[str, float]:
        return {
            AccountType.SAVINGS.value: minimum_balance_for(AccountType.SAVINGS),
            AccountType.CURRENT.value: minimum_balance_for(AccountType.CURRENT),
            AccountType.SALARY.value: minimum_balance_for(AccountType.SALARY),
        }

    def loan_sections(self) -> list[str]:
        return list_loan_sections()

    def _require_customer(self, customer_id: str) -> Customer:
        if customer_id not in self.customers:
            raise ValueError("Customer not found.")
        return self.customers[customer_id]

    def _require_account(self, account_number: str) -> BankAccount:
        if account_number not in self.accounts:
            raise ValueError("Account not found.")
        return self.accounts[account_number]

    def _require_loan(self, loan_id: str) -> LoanApplication:
        if loan_id not in self.loans:
            raise ValueError("Loan not found.")
        return self.loans[loan_id]

    def _require_debit_card(self, card_number: str) -> DebitCard:
        if card_number not in self.debit_cards:
            raise ValueError("Debit card not found.")
        return self.debit_cards[card_number]

    def _require_credit_card(self, card_number: str) -> CreditCard:
        if card_number not in self.credit_cards:
            raise ValueError("Credit card not found.")
        return self.credit_cards[card_number]
