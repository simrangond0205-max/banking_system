"""Flask web UI for the banking system."""

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from loans import LOAN_POLICY, LoanType
from models import AccountType
from storage import BACKUP_JSON, BankRepository, DEFAULT_DB, load_bank

app = Flask(__name__, template_folder=str(Path(__file__).resolve().parent))
app.secret_key = os.environ.get("SECRET_KEY", "dev-banking-secret-change-in-production")

_repo = BankRepository(DEFAULT_DB)


def get_bank():
    return _repo.load()


@app.context_processor
def inject_globals():
    bank = get_bank()
    return {
        "loan_sections": bank.loan_sections(),
        "min_balances": bank.get_minimum_balances(),
        "service_categories": [
            "Account & Balance",
            "Debit Card",
            "Credit Card",
            "Loans",
            "Transactions & Disputes",
            "Branch & ATM",
            "General Inquiry",
        ],
    }


@app.route("/")
def home():
    bank = get_bank()
    return render_template(
        "home.html",
        customers=list(bank.customers.values()),
        accounts=list(bank.accounts.values()),
        loans=list(bank.loans.values()),
    )


@app.route("/customers", methods=["GET", "POST"])
def customers():
    bank = get_bank()
    if request.method == "POST":
        try:
            c = bank.register_customer(
                request.form["name"].strip(),
                request.form["email"].strip(),
                request.form["phone"].strip(),
            )
            flash(f"Customer registered: {c.customer_id}", "success")
        except ValueError as e:
            flash(str(e), "error")
        return redirect(url_for("customers"))
    return render_template("customers.html", customers=list(bank.customers.values()))


@app.route("/accounts", methods=["GET", "POST"])
def accounts():
    bank = get_bank()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "open":
                types = {
                    "Savings": AccountType.SAVINGS,
                    "Current": AccountType.CURRENT,
                    "Salary": AccountType.SALARY,
                }
                acct = bank.open_account(
                    request.form["customer_id"].strip(),
                    types[request.form["account_type"]],
                    float(request.form["initial_deposit"]),
                )
                flash(f"Account opened: {acct.account_number}", "success")
            elif action == "deposit":
                bank.deposit(request.form["account_number"].strip(), float(request.form["amount"]))
                flash("Deposit successful.", "success")
            elif action == "withdraw":
                bank.withdraw(request.form["account_number"].strip(), float(request.form["amount"]))
                flash("Withdrawal successful.", "success")
        except (ValueError, KeyError, TypeError) as e:
            flash(str(e), "error")
        return redirect(url_for("accounts"))
    return render_template(
        "accounts.html",
        customers=list(bank.customers.values()),
        accounts=list(bank.accounts.values()),
    )


@app.route("/cards", methods=["GET", "POST"])
def cards():
    bank = get_bank()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "debit_issue":
                card = bank.issue_debit_card(
                    request.form["account_number"].strip(),
                    request.form["pin"].strip(),
                )
                flash(f"Debit card issued: {card.card_number}", "success")
            elif action == "debit_pay":
                bank.debit_purchase(
                    request.form["debit_card_number"].strip(),
                    request.form["pin"].strip(),
                    float(request.form["amount"]),
                )
                flash("Debit purchase successful.", "success")
            elif action == "credit_issue":
                card = bank.issue_credit_card(
                    request.form["customer_id"].strip(),
                    float(request.form["credit_limit"]),
                )
                flash(f"Credit card issued: {card.card_number}", "success")
            elif action == "credit_pay":
                bank.pay_credit_card(
                    request.form["credit_card_number"].strip(),
                    float(request.form["amount"]),
                )
                flash("Credit card payment recorded.", "success")
            elif action == "credit_swipe":
                bank.credit_purchase(
                    request.form["credit_card_number"].strip(),
                    float(request.form["amount"]),
                )
                flash("Credit purchase successful.", "success")
        except (ValueError, KeyError, TypeError) as e:
            flash(str(e), "error")
        return redirect(url_for("cards"))
    return render_template(
        "cards.html",
        customers=list(bank.customers.values()),
        accounts=list(bank.accounts.values()),
        debit_cards=list(bank.debit_cards.values()),
        credit_cards=list(bank.credit_cards.values()),
    )


@app.route("/loans", methods=["GET", "POST"])
def loans_page():
    bank = get_bank()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "apply":
                loan_type = LoanType(request.form["loan_type"])
                app_loan = bank.apply_loan(
                    request.form["customer_id"].strip(),
                    loan_type,
                    float(request.form["amount"]),
                    int(request.form["tenure_months"]),
                )
                flash(f"Loan applied: {app_loan.loan_id}", "success")
            elif action == "disburse":
                bank.approve_and_disburse_loan(
                    request.form["loan_id"].strip(),
                    request.form["account_number"].strip(),
                )
                flash("Loan approved and disbursed.", "success")
            elif action == "emi":
                amount_raw = request.form.get("amount", "").strip()
                amount = float(amount_raw) if amount_raw else None
                bank.pay_loan_emi(request.form["loan_id"].strip(), amount)
                flash("EMI payment recorded.", "success")
        except (ValueError, KeyError, TypeError) as e:
            flash(str(e), "error")
        return redirect(url_for("loans_page"))
    policies = {lt.value: LOAN_POLICY[lt] for lt in LoanType}
    return render_template(
        "loans.html",
        customers=list(bank.customers.values()),
        accounts=list(bank.accounts.values()),
        loans=list(bank.loans.values()),
        policies=policies,
    )


@app.route("/support", methods=["GET", "POST"])
def support():
    bank = get_bank()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "ticket":
                t = bank.create_support_ticket(
                    request.form["customer_id"].strip(),
                    request.form["category"].strip(),
                    request.form["subject"].strip(),
                )
                flash(f"Ticket created: {t.ticket_id}", "success")
            elif action == "faq":
                ans = bank.service.lookup_faq(request.form["keyword"].strip())
                flash(ans or "No FAQ match found.", "info")
        except ValueError as e:
            flash(str(e), "error")
        return redirect(url_for("support"))
    return render_template(
        "support.html",
        customers=list(bank.customers.values()),
        tickets=list(bank.service.tickets),
        contact=bank.service.contact_info(),
    )


@app.route("/backup", methods=["GET", "POST"])
def backup():
    bank = get_bank()
    backup_path = BACKUP_JSON
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "export":
                _repo.export_json(bank, backup_path)
                flash(f"Exported to {backup_path.name}", "success")
            elif action == "import":
                if not backup_path.is_file():
                    raise ValueError("No backup.json found. Export a backup first.")
                _repo.import_json(backup_path)
                flash("Imported from backup.json", "success")
        except (ValueError, OSError, json.JSONDecodeError) as e:
            flash(str(e), "error")
        return redirect(url_for("backup"))
    return render_template("backup.html", backup_file=backup_path.name)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
