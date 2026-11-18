# Rohobot Job Matching

Rohobot is a local-development job-matching application with a Next.js frontend, a Python FastAPI backend, and PostgreSQL. The backend uses SQLAlchemy and Alembic migrations.

# What the team needs

- Windows 10/11 and PowerShell
- Node.js 20.9 or later (npm is included)
- Python 3.12 recommended
- PostgreSQL 16, either installed on Windows or run with Docker Desktop
- Git (optional, for sharing source-code changes)

The Python Launcher (`py`) is convenient but optional. If `py` is not recognized, use the full path to `python.exe` in the virtual-environment instructions below.

# Get the project ready

Open PowerShell in the project root (the folder containing `package.json` and `docker-compose.yml`). Replace `C:\path\to\rohobot-jobmatching-connected` in the examples with the location where you extracted the project:

```powershell
cd C:\path\to\rohobot-jobmatching-connected
```

Install the frontend dependencies:

```powershell
npm ci
```

Create the frontend environment file if it does not exist:

```powershell
if (!(Test-Path .env.local)) {
  Set-Content .env.local "NEXT_PUBLIC_API_URL=http://localhost:8000/api"
}
```

# Configure PostgreSQL

Choose **one** database option below. The database server, database name, port, username, and password in `backend\.env` must all refer to the same PostgreSQL instance.

#Option A: PostgreSQL installed on Windows

1. Make sure the PostgreSQL Windows service is running.
2. Use pgAdmin or SQL Shell (psql) to connect to the server as the PostgreSQL administrator, commonly `postgres`.
3. In the SQL Shell, commands are entered only after the prompt appears, for example `postgres=#`. If the `rohobot` role and database do not already exist, run:

   ```sql
   CREATE ROLE rohobot WITH LOGIN;
   \password rohobot
   CREATE DATABASE rohobot OWNER rohobot;
   ```

   Enter a password when `\password` prompts you. Do not paste PowerShell commands such as `cd` into SQL Shell. If the role or database already exists, do not create it again.

4. In a separate PowerShell window, create the backend environment file and edit it:

   ```powershell
   cd C:\path\to\rohobot-jobmatching-connected\backend
   if (!(Test-Path .env)) { Copy-Item .env.example .env }
   notepad .env
   ```

5. Set `DATABASE_URL` in `backend\.env` to match your installed server. Use the actual port shown by your PostgreSQL installation (for example, `5433` if that is the port you configured):

   text
   DATABASE_URL=postgresql+psycopg://rohobot:YOUR_PASSWORD@localhost:5433/rohobot
   

   Replace `YOUR_PASSWORD` locally. Keep this secret out of chat and source control. For simple local configuration, use a password without URL-reserved characters; otherwise URL-encode special characters in the connection URL.

# Option B: PostgreSQL with Docker Desktop

Start Docker Desktop, then from the project root run:

powershell
docker compose up -d db


The provided Compose file maps PostgreSQL to port `5432`, with local-development defaults:

- Database: `rohobot`
- Username: `rohobot`
- Password: `rohobot`
- Port: `5432`

For this option, set `DATABASE_URL` in `backend\.env` to:

text
DATABASE_URL=postgresql+psycopg://rohobot:rohobot@localhost:5432/rohobot


The Docker database stores its data in the named volume `rohobot-postgres-data`. Avoid running Docker PostgreSQL and installed PostgreSQL on the same host port at the same time. If they use different ports, make sure the backend and pgAdmin are pointed at the intended one.

# Set up and start the backend

Open a PowerShell window and create a virtual environment in `backend`:

powershell
cd C:\path\to\rohobot-jobmatching-connected\backend
py -3.12 -m venv .venv


If `py` is not recognized, replace `py -3.12` with the full path to the Python 3.12 executable. For example:

powershell
& "$env:LocalAppData\Programs\Python\Python312\python.exe" -m venv .venv


Install backend dependencies, create `.env` if you have not already created it in the database step, apply migrations, then start the API:

powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
`

Keep this terminal open while using the app. Check the API at:

- Health check: <http://localhost:8000/api/health>
- Interactive API documentation: <http://localhost:8000/docs>

The health endpoint should return `{"status":"ok","database":"ok"}`. If it reports a database error, verify the `DATABASE_URL` port and credentials, and check that the matching PostgreSQL server is running.

## Create an administrator

In a **second** PowerShell window:

```powershell
cd C:\path\to\rohobot-jobmatching-connected\backend
.\.venv\Scripts\python.exe -m app.create_user --role admin --email admin@example.com --name "Local Admin"
```

Enter a password of at least 12 characters when prompted. The command creates the account in the database configured by `backend\.env`. Sign in with that email and password, selecting the **Admin** role.

To reset the password for an existing admin:

```powershell
.\.venv\Scripts\python.exe -m app.reset_password --email admin@example.com
```

The reset command prompts for the new password twice and signs out existing sessions. Passwords are stored as hashes and cannot be viewed in the database.

# Start the frontend

Open another PowerShell window and run:

powershell
cd C:\path\to\rohobot-jobmatching-connected
npm run dev


Open <http://localhost:3000>. Keep both the frontend and backend terminal windows running. The frontend calls the Python API at `http://localhost:8000/api`.

## Browse the database

In pgAdmin, register/connect to the same PostgreSQL server configured in `backend\.env`:

- Host: `localhost`
- Port: use the port from `DATABASE_URL` (commonly `5432` for Docker or the installed server's configured port)
- Database: `rohobot`
- Username: `rohobot`
- Password: the password from `DATABASE_URL`

Browse **Databases → rohobot → Schemas → public → Tables**. Right-click a table and choose **View/Edit Data → All Rows**. Right-click **Tables** and select **Refresh** if needed.

Useful tables:

- `users`: account email, role, active state, and password hash (do not share password hashes)
- `employer_profiles`: organization details; additional fields are in the `profile_data` JSON column
- `candidate_profiles`: candidate profile information
- `jobs` and `job_applications`: job postings and applications
- `application_records`: workflow and payment transaction records
- `email_outbox`: email records and delivery state

The `users` table can be empty until accounts are registered or created. Organization records appear after an employer account is created; further organization details are saved during employer setup.

# Email and payments

- Email records are saved in PostgreSQL. With SMTP unset, messages are not delivered; local development verification codes may appear in the registration flow, and outbox records can be inspected in the app.
- Online Chapa checkout is disabled by default. To enable it, configure the Chapa settings in `backend\.env` using backend-only credentials. Never put payment secrets in frontend variables such as `NEXT_PUBLIC_*`.
- A real Chapa callback/webhook requires a publicly reachable HTTPS backend URL. Localhost is not reachable by the payment provider. Test with provider test credentials before enabling live payments.
- Candidate documents are stored in PostgreSQL. The current API enforces a 10 MB per-file and 25 MB per-request limit.

# Troubleshooting

- `py` is not recognized: install Python 3.12 and the Python Launcher, or create the virtual environment using the full path to `python.exe`.
- Password authentication failed: the username/password in `backend\.env` must match the PostgreSQL role password. Confirm you edited the `.env` in this project folder.
- Connection refused / database unavailable: start the matching PostgreSQL service or Docker container and check the port in `DATABASE_URL`.
- Migrations succeed but pgAdmin shows no tables: pgAdmin may be connected to another PostgreSQL server or port. Check `DATABASE_URL`, reconnect to that exact instance and database, then refresh **Schemas → public → Tables.
- `ERR_EMPTY_RESPONSE` on port 5432: PostgreSQL is not a website. Use pgAdmin or `psql` to browse the database.
- `localhost:8000` shows Not Found: use `/api/health` or `/docs`; the API does not provide a homepage at `/`.
- `Failed to fetch` in the frontend: ensure the backend is running on port `8000`, then open <http://localhost:8000/api/health>.
- Login says account is incorrect or unverified: check the selected role, email, password, and email-verification state. The local API and frontend must use the same project and database.

# Team and security notes

- Share the source code and this README with the team, but do not share `.env`, `.env.local`, passwords, API keys, personal documents, or production database exports.
- `.env` files and local virtual environments are machine-specific and should not be committed. Each teammate should create their own environment files and Python virtual environment.
- Database contents are stored separately from source code. For Docker, persist data with the named volume; for an installed PostgreSQL server, use that server's backup tools.
- The default Docker credentials are for local development only. Use strong, private credentials and appropriate backups, HTTPS, monitoring, data-retention, and access controls before production use.

Checks

From the project root:

powershell
npm run lint
npm run build


From `backend`:

powershell
.\.venv\Scripts\python.exe -m compileall -q app migrations

#   r o h e b o t - j o b - m a t c h e r  
 