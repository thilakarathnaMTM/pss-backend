# Energy Optimization API (FastAPI)

Backend for the Apex Energy SME garment factory optimizer.

## Requirements

- Python 3.10+
- pip

## Setup

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

## Environment (optional)

Create a `.env` in the backend root if you want to override defaults:

```env
PROJECT_NAME=Energy Optimization API
API_V1_STR=/api/v1
SECRET_KEY=change-me-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
DATABASE_URL=sqlite+aiosqlite:///./energy.db
```

Defaults already exist in `app/core/config.py`. SQLite DB file `energy.db` is created on first run.

## Run

From the **backend root** (with venv activated):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  
- Health: http://localhost:8000/

On startup the app creates tables and seeds:

- Email: `manager@abcgarments.lk`
- Password: `energy@2024`

## Project layout

```text
backend/
├── app/
│   ├── main.py
│   ├── api/v1/endpoints/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── services/
├── requirements.txt
└── README.md
```

## bcrypt / passlib note

This project uses:

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

`passlib` relies on the older bcrypt interface. Use:

```txt
bcrypt==4.0.1
```

Do not install `bcrypt>=4.1` or you may see errors like:

```text
AttributeError: module 'bcrypt' has no attribute '__about__'
```

## Freeze dependencies again

```bash
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip freeze > requirements.txt
```

## Common commands

```bash
# install
pip install -r requirements.txt

# run
uvicorn app.main:app --reload --port 8000

# deactivate venv
deactivate
```
