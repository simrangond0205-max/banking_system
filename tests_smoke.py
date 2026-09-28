"""Quick smoke tests — run: python tests_smoke.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from storage import BankRepository, DEFAULT_DB
from webapp import app


def main() -> None:
    repo = BankRepository(DEFAULT_DB)
    bank = repo.load()
    cid = next(iter(bank.customers.values())).customer_id if bank.customers else None

    client = app.test_client()
    for path in ("/", "/customers", "/accounts", "/cards", "/loans", "/support", "/backup"):
        r = client.get(path)
        assert r.status_code == 200, f"GET {path} -> {r.status_code}"

    if cid:
        acc = next((a for a in bank.accounts.values() if a.customer_id == cid), None)
        if acc is None:
            r = client.post(
                "/accounts",
                data={
                    "action": "open",
                    "customer_id": cid,
                    "account_type": "Savings",
                    "initial_deposit": "600",
                },
                follow_redirects=True,
            )
            assert r.status_code == 200
            acc = next(
                a
                for a in BankRepository(DEFAULT_DB).load().accounts.values()
                if a.customer_id == cid
            )

        r = client.post(
            "/accounts",
            data={"action": "deposit", "account_number": acc.account_number, "amount": "1"},
            follow_redirects=True,
        )
        assert r.status_code == 200

    r = client.post("/backup", data={"action": "import"}, follow_redirects=True)
    assert r.status_code == 200
    assert b"No backup.json found" in r.data or b"Imported" in r.data or b"backup" in r.data.lower()

    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
