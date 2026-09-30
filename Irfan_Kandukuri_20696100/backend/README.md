# POC-07 Backend

FastAPI backend for Inventory Management and Procurement System.

## Run

1. Create virtual environment
2. Install dependencies from requirements.txt
3. Copy .env.example to .env and adjust values

Start from backend folder:
- cd c:\Users\SH20695879\Desktop\inventory_management_phase1\backend
- .\.venv\Scripts\python.exe -m pip install -r requirements.txt
- .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Start from workspace root:
- cd c:\Users\SH20695879\Desktop\inventory_management_phase1
- c:\Users\SH20695879\Desktop\inventory_management_phase1\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir c:\Users\SH20695879\Desktop\inventory_management_phase1\backend --host 127.0.0.1 --port 8000

Swagger docs:
- /docs
- /redoc

## Local Development Login

The backend seeds one reusable manager account on startup when `SEED_DEV_USER=true`:

- Username: `manager@poc07.com`
- Password: `Password@123`

Set `SEED_DEV_USER=false` and provide different `DEV_USER_EMAIL` and `DEV_USER_PASSWORD` values for another environment.
