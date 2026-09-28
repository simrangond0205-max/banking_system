"""SQLite persistence and JSON backup for the banking system."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from loans import LoanApplication, LoanStatus, LoanType
from models import (
    AccountType,
    BankAccount,
    CreditCard,
    Customer,
    DebitCard,
    SupportTicket,
)


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_DIR))
DEFAULT_DB = DATA_DIR / "bank.db"
BACKUP_JSON = DATA_DIR / "backup.json"


class BankRepository:
    def __init__(self, db_path: Path | str = DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self._migrate_legacy_db()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _migrate_legacy_db(self) -> None:
        if self.db_path.is_file():
            return
        legacy = PROJECT_DIR / "data" / "bank.db"
        if legacy.is_file():
            import shutil

            shutil.copy2(legacy, self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS accounts (
                    account_number TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    balance REAL NOT NULL,
                    transactions_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS debit_cards (
                    card_number TEXT PRIMARY KEY,
                    account_number TEXT NOT NULL,
                    daily_limit REAL NOT NULL,
                    pin_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL,
                    spent_today REAL NOT NULL,
                    spent_date TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS credit_cards (
                    card_number TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    credit_limit REAL NOT NULL,
                    outstanding REAL NOT NULL,
                    is_active INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS loans (
                    loan_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    loan_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    tenure_months INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    emi REAL NOT NULL,
                    balance REAL NOT NULL,
                    payments_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS support_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                """
            )

    def _get_meta(self, conn: sqlite3.Connection, key: str, default: str) -> str:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def _set_meta(self, conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def load(self) -> "BankingSystem":
        from bank import BankingSystem

        bank = BankingSystem(repository=self)
        with self._connect() as conn:
            seq = int(self._get_meta(conn, "next_customer_seq", "1"))
            bank._next_customer_seq = seq

            for row in conn.execute("SELECT * FROM customers"):
                bank.customers[row["customer_id"]] = Customer(
                    customer_id=row["customer_id"],
                    name=row["name"],
                    email=row["email"],
                    phone=row["phone"],
                )

            for row in conn.execute("SELECT * FROM accounts"):
                bank.accounts[row["account_number"]] = BankAccount(
                    account_number=row["account_number"],
                    customer_id=row["customer_id"],
                    account_type=AccountType(row["account_type"]),
                    balance=row["balance"],
                    transactions=json.loads(row["transactions_json"]),
                )

            for row in conn.execute("SELECT * FROM debit_cards"):
                bank.debit_cards[row["card_number"]] = DebitCard(
                    card_number=row["card_number"],
                    account_number=row["account_number"],
                    daily_limit=row["daily_limit"],
                    pin_hash=row["pin_hash"],
                    is_active=bool(row["is_active"]),
                    spent_today=row["spent_today"],
                    spent_date=row["spent_date"],
                )

            for row in conn.execute("SELECT * FROM credit_cards"):
                bank.credit_cards[row["card_number"]] = CreditCard(
                    card_number=row["card_number"],
                    customer_id=row["customer_id"],
                    credit_limit=row["credit_limit"],
                    outstanding=row["outstanding"],
                    is_active=bool(row["is_active"]),
                )

            for row in conn.execute("SELECT * FROM loans"):
                bank.loans[row["loan_id"]] = LoanApplication(
                    loan_id=row["loan_id"],
                    customer_id=row["customer_id"],
                    loan_type=LoanType(row["loan_type"]),
                    amount=row["amount"],
                    tenure_months=row["tenure_months"],
                    status=LoanStatus(row["status"]),
                    emi=row["emi"],
                    balance=row["balance"],
                    payments=json.loads(row["payments_json"]),
                )

            for row in conn.execute("SELECT * FROM support_tickets"):
                bank.service.tickets.append(
                    SupportTicket(
                        ticket_id=row["ticket_id"],
                        customer_id=row["customer_id"],
                        category=row["category"],
                        subject=row["subject"],
                        status=row["status"],
                    )
                )
        return bank

    def save(self, bank: "BankingSystem") -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM customers")
            conn.execute("DELETE FROM accounts")
            conn.execute("DELETE FROM debit_cards")
            conn.execute("DELETE FROM credit_cards")
            conn.execute("DELETE FROM loans")
            conn.execute("DELETE FROM support_tickets")

            self._set_meta(conn, "next_customer_seq", str(bank._next_customer_seq))

            for c in bank.customers.values():
                conn.execute(
                    "INSERT INTO customers VALUES (?, ?, ?, ?)",
                    (c.customer_id, c.name, c.email, c.phone),
                )

            for a in bank.accounts.values():
                conn.execute(
                    "INSERT INTO accounts VALUES (?, ?, ?, ?, ?)",
                    (
                        a.account_number,
                        a.customer_id,
                        a.account_type.value,
                        a.balance,
                        json.dumps(a.transactions),
                    ),
                )

            for d in bank.debit_cards.values():
                conn.execute(
                    "INSERT INTO debit_cards VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        d.card_number,
                        d.account_number,
                        d.daily_limit,
                        d.pin_hash,
                        int(d.is_active),
                        d.spent_today,
                        d.spent_date,
                    ),
                )

            for c in bank.credit_cards.values():
                conn.execute(
                    "INSERT INTO credit_cards VALUES (?, ?, ?, ?, ?)",
                    (
                        c.card_number,
                        c.customer_id,
                        c.credit_limit,
                        c.outstanding,
                        int(c.is_active),
                    ),
                )

            for loan in bank.loans.values():
                conn.execute(
                    "INSERT INTO loans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        loan.loan_id,
                        loan.customer_id,
                        loan.loan_type.value,
                        loan.amount,
                        loan.tenure_months,
                        loan.status.value,
                        loan.emi,
                        loan.balance,
                        json.dumps(loan.payments),
                    ),
                )

            for t in bank.service.tickets:
                conn.execute(
                    "INSERT INTO support_tickets VALUES (?, ?, ?, ?, ?)",
                    (t.ticket_id, t.customer_id, t.category, t.subject, t.status),
                )

    def export_json(self, bank: "BankingSystem", path: Path | str) -> None:
        payload = _bank_to_dict(bank)
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def import_json(self, path: Path | str) -> "BankingSystem":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        bank = _bank_from_dict(payload)
        bank.repository = self
        self.save(bank)
        return bank


def load_bank(db_path: Path | str = DEFAULT_DB) -> "BankingSystem":
    return BankRepository(db_path).load()


def _bank_to_dict(bank: "BankingSystem") -> dict[str, Any]:
    return {
        "next_customer_seq": bank._next_customer_seq,
        "customers": [asdict(c) for c in bank.customers.values()],
        "accounts": [
            {
                **asdict(a),
                "account_type": a.account_type.value,
            }
            for a in bank.accounts.values()
        ],
        "debit_cards": [asdict(d) for d in bank.debit_cards.values()],
        "credit_cards": [asdict(c) for c in bank.credit_cards.values()],
        "loans": [
            {
                **asdict(loan),
                "loan_type": loan.loan_type.value,
                "status": loan.status.value,
            }
            for loan in bank.loans.values()
        ],
        "tickets": [asdict(t) for t in bank.service.tickets],
    }


def _bank_from_dict(data: dict[str, Any]) -> "BankingSystem":
    from bank import BankingSystem

    bank = BankingSystem()
    bank._next_customer_seq = int(data.get("next_customer_seq", 1))
    for c in data.get("customers", []):
        bank.customers[c["customer_id"]] = Customer(**c)
    for a in data.get("accounts", []):
        bank.accounts[a["account_number"]] = BankAccount(
            account_number=a["account_number"],
            customer_id=a["customer_id"],
            account_type=AccountType(a["account_type"]),
            balance=a["balance"],
            transactions=a.get("transactions", []),
        )
    for d in data.get("debit_cards", []):
        if "pin_hash" not in d and "pin" in d:
            from models import hash_pin

            d["pin_hash"] = hash_pin(d.pop("pin"))
        d.pop("pin", None)
        bank.debit_cards[d["card_number"]] = DebitCard(**d)
    for c in data.get("credit_cards", []):
        bank.credit_cards[c["card_number"]] = CreditCard(**c)
    for loan in data.get("loans", []):
        bank.loans[loan["loan_id"]] = LoanApplication(
            loan_id=loan["loan_id"],
            customer_id=loan["customer_id"],
            loan_type=LoanType(loan["loan_type"]),
            amount=loan["amount"],
            tenure_months=loan["tenure_months"],
            status=LoanStatus(loan["status"]),
            emi=loan["emi"],
            balance=loan["balance"],
            payments=loan.get("payments", []),
        )
    for t in data.get("tickets", []):
        bank.service.tickets.append(SupportTicket(**t))
    return bank
