# Python Banking System (Full Stack)

Console + web banking app with SQLite persistence, JSON backup, PIN-validated debit cards, credit cards, all loan sections, customer service, and minimum balance rules.

## Features

- **Accounts**: Savings, Current, Salary with minimum balance enforcement
- **Debit card**: Hashed PIN, daily limit, purchase with PIN validation
- **Credit card**: Limit, purchases, minimum due, payments
- **Loan sections**: Home, Personal, Auto, Education, Business, Gold, Agriculture
- **Customer service**: Tickets, FAQ, contact info
- **Persistence**: SQLite (`bank.db` in project folder) auto-save on every change
- **Backup**: Export/import JSON from CLI or web

## Setup

```bash
cd C:\Users\Mayank\banking_system
pip install -r requirements.txt
```

## Run CLI (data saved to SQLite)

```bash
python main.py
python main.py --demo
```

## Run Web UI (Flask)

```bash
python webapp.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Deploy (production)

**Windows** (Waitress):

```bash
pip install -r requirements.txt
set SECRET_KEY=your-long-random-secret
set PORT=8080
python serve_production.py
```

**Linux / macOS** (Gunicorn):

```bash
pip install -r requirements.txt
export SECRET_KEY=your-long-random-secret
export PORT=8080
gunicorn --bind 0.0.0.0:$PORT --workers 2 webapp:app
```

**Docker** (persistent SQLite in `/data`):

```bash
docker build -t banking-system .
docker run -p 8080:8080 -v banking_data:/data -e SECRET_KEY=your-long-random-secret banking-system
```

**Render**: push this folder to GitHub, connect the repo on [Render](https://render.com), and use the included `render.yaml` (Blueprint) or set start command to the Gunicorn line above. Set `SECRET_KEY` in the dashboard.

**Railway / Heroku-style**: deploy with the included `Procfile`; set `SECRET_KEY` and let the platform set `PORT`.

Optional: `DATA_DIR` points SQLite and `backup.json` at a writable path (required for ephemeral containers if you need data to survive restarts).

## Minimum balance

| Account | Minimum |
|---------|---------|
| Savings | 500 |
| Current | 1000 |
| Salary | 0 |

## Project folder (everything in one place)

All code, web pages, and data live in `C:\Users\Mayank\banking_system`:

| File | Purpose |
|------|---------|
| `main.py` | Terminal menu |
| `webapp.py` | Flask web application |
| `bank.py` | Business logic |
| `storage.py` | SQLite + JSON |
| `models.py` | Accounts, cards, customers |
| `loans.py` | Loan types and EMI |
| `customer_service.py` | Support desk |
| `constants.py` | Policy limits |
| `home.html`, `accounts.html`, … | Web UI pages |
| `bank.db` | Saved bank data (created on first run) |
| `backup.json` | Optional JSON export |


https://dashboard.render.com/web/srv-dat9pc67bikc73c8f3v0 this is my live website
