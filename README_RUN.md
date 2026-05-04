# Sporting Edge Local Run Guide

This repo is a FastAPI app with static HTML, CSS, and JavaScript served by `main.py`.

## 1. Create a virtual environment

```powershell
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Mac/Linux:

```bash
source .venv/bin/activate
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Add environment variables

Copy `.env.example` to `.env`, then add any provider keys you have.

Do not commit `.env`.

## 4. Run the app

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

## 5. Run tests

```bash
pytest -q
```

Without provider keys, the app should show clean empty states such as `Live provider not connected.` instead of fake live betting data.
