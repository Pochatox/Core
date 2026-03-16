poetry run python create_db.py
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8282
