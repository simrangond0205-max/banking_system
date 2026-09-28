"""Interactive CLI for the Python banking system."""

from __future__ import annotations

import sys

from bank import BankingSystem
from constants import LOAN_TYPES
from customer_service import SERVICE_CATEGORIES
from loans import LoanType
from models import AccountType
from storage import BACKUP_JSON, BankRepository, DEFAULT_DB, load_bank


def _read_float(prompt: str) -> float:
    return float(input(prompt))


def _read_int(prompt: str) -> int:
    return int(input(prompt))


def print_loan_sections() -> None:
    print("\n--- Loan sections ---")
    for i, name in enumerate(LOAN_TYPES, start=1):
        print(f"  {i}. {name}")


def print_minimum_balances(bank: BankingSystem) -> None:
    print("\n--- Minimum balance (amounts) ---")
    for acct_type, min_bal in bank.get_minimum_balances().items():
        print(f"  {acct_type}: {min_bal:.2f}")


def menu(bank: BankingSystem) -> None:
    while True:
        print(
            "\n========== MY BANK ==========\n"
            "1. Register customer\n"
            "2. Open account (with minimum balance check)\n"
            "3. Deposit / Withdraw\n"
            "4. Issue debit card / Debit purchase (PIN)\n"
            "5. Issue credit card / Pay or purchase\n"
            "6. Loan section (view types, apply, approve & disburse)\n"
            "7. Customer service (ticket, FAQ, contact)\n"
            "8. View minimum balances & loan amounts policy\n"
            "9. Export JSON backup\n"
            "0. Exit\n"
        )
        choice = input("Choose option: ").strip()

        try:
            if choice == "1":
                name = input("Name: ").strip()
                email = input("Email: ").strip()
                phone = input("Phone: ").strip()
                c = bank.register_customer(name, email, phone)
                print(f"Registered {c.name} | ID: {c.customer_id}")

            elif choice == "2":
                cid = input("Customer ID: ").strip()
                print("Account types: 1=Savings 2=Current 3=Salary")
                t = _read_int("Type: ")
                types = [AccountType.SAVINGS, AccountType.CURRENT, AccountType.SALARY]
                dep = _read_float("Initial deposit: ")
                acct = bank.open_account(cid, types[t - 1], dep)
                print("Opened:", acct.summary())

            elif choice == "3":
                acc = input("Account number: ").strip()
                op = input("d=deposit w=withdraw: ").strip().lower()
                amt = _read_float("Amount: ")
                if op == "d":
                    bank.deposit(acc, amt)
                else:
                    bank.withdraw(acc, amt)
                print(bank.accounts[acc].summary())

            elif choice == "4":
                sub = input("i=issue p=purchase: ").strip().lower()
                if sub == "i":
                    acc = input("Account number: ").strip()
                    pin = input("4-digit PIN: ").strip()
                    card = bank.issue_debit_card(acc, pin)
                    print(f"Debit card issued: {card.card_number} | Daily limit: {card.daily_limit:.2f}")
                else:
                    num = input("Debit card number: ").strip()
                    pin = input("PIN: ").strip()
                    amt = _read_float("Amount: ")
                    bank.debit_purchase(num, pin, amt)
                    print("Debit purchase OK.")

            elif choice == "5":
                sub = input("i=issue p=pay s=purchase: ").strip().lower()
                if sub == "i":
                    cid = input("Customer ID: ").strip()
                    limit = _read_float("Credit limit: ")
                    card = bank.issue_credit_card(cid, limit)
                    print(card.summary())
                elif sub == "p":
                    num = input("Card number: ").strip()
                    amt = _read_float("Payment amount: ")
                    bank.pay_credit_card(num, amt)
                    print(bank.credit_cards[num].summary())
                else:
                    num = input("Card number: ").strip()
                    amt = _read_float("Purchase amount: ")
                    bank.credit_purchase(num, amt)
                    print(bank.credit_cards[num].summary())

            elif choice == "6":
                print_loan_sections()
                sub = input("a=apply v=view e=pay emi: ").strip().lower()
                if sub == "a":
                    cid = input("Customer ID: ").strip()
                    print_loan_sections()
                    idx = _read_int("Loan type number: ")
                    loan_type = list(LoanType)[idx - 1]
                    amount = _read_float("Loan amount: ")
                    tenure = _read_int("Tenure (months): ")
                    app = bank.apply_loan(cid, loan_type, amount, tenure)
                    print("Applied:", app.policy_summary())
                    if input("Approve & disburse now? (y/n): ").strip().lower() == "y":
                        acc = input("Credit to account number: ").strip()
                        bank.approve_and_disburse_loan(app.loan_id, acc)
                        print("Disbursed:", bank.loans[app.loan_id].policy_summary())
                elif sub == "e":
                    lid = input("Loan ID: ").strip()
                    bank.pay_loan_emi(lid)
                    print(bank.loans[lid].policy_summary())
                else:
                    for loan in bank.loans.values():
                        print(loan.policy_summary())

            elif choice == "7":
                print(bank.service.contact_info())
                print("Categories:", ", ".join(SERVICE_CATEGORIES))
                sub = input("t=ticket f=FAQ: ").strip().lower()
                if sub == "t":
                    cid = input("Customer ID: ").strip()
                    cat = input("Category (exact name): ").strip()
                    subj = input("Subject: ").strip()
                    t = bank.create_support_ticket(cid, cat, subj)
                    print(f"Ticket {t.ticket_id} created ({t.status})")
                else:
                    kw = input("FAQ keyword: ").strip()
                    ans = bank.service.lookup_faq(kw)
                    print(ans or "No FAQ match. Call customer service.")

            elif choice == "8":
                print_minimum_balances(bank)
                print("\n--- Loan amount ranges (min – max) ---")
                from loans import LOAN_POLICY

                for lt in LoanType:
                    p = LOAN_POLICY[lt]
                    print(
                        f"  {lt.value}: {p['min_amount']:.0f} – {p['max_amount']:.0f} "
                        f"@ {p['rate_percent']}% up to {int(p['max_tenure_months'])} months"
                    )

            elif choice == "9":
                if bank.repository:
                    path = BACKUP_JSON
                    bank.repository.export_json(bank, path)
                    print(f"Exported to {path}")
                else:
                    print("No repository attached.")

            elif choice == "0":
                print("Thank you for banking with us.")
                sys.exit(0)
            else:
                print("Invalid option.")

        except (ValueError, KeyError, IndexError) as e:
            print(f"Error: {e}")


def demo() -> None:
    """Non-interactive demo when run with --demo."""
    repo = BankRepository(DEFAULT_DB)
    bank = repo.load()
    c = bank.register_customer("Asha Kumar", "asha@example.com", "9876500000")
    acct = bank.open_account(c.customer_id, AccountType.SAVINGS, 10_000)
    bank.issue_debit_card(acct.account_number, "1234")
    debit_num = next(iter(bank.debit_cards))
    bank.debit_purchase(debit_num, "1234", 500)
    bank.issue_credit_card(c.customer_id, 50_000)
    loan = bank.apply_loan(c.customer_id, LoanType.PERSONAL, 100_000, 24)
    bank.approve_and_disburse_loan(loan.loan_id, acct.account_number)
    print("Demo customer:", c.customer_id)
    print("Account:", acct.summary())
    print("Loan sections:", ", ".join(bank.loan_sections()))
    print_minimum_balances(bank)
    print(bank.service.contact_info())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        menu(load_bank())
