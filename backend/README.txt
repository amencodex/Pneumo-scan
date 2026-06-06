PneumoScan local backend

What it does:

- Local signup and login
- Stores users in data\pneumoscan.db
- Stores uploaded X-rays in uploads\
- Runs your local models\pneumonia_model.json
- Saves scan results and daily check-ins
- Shows dashboard, history, and safe recovery guidance

Install dependencies:

python -m pip install -r requirements.txt

Run:

python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

Then open:

http://127.0.0.1:8000

Safety:

This is not a medical device. It cannot diagnose pneumonia or cure pneumonia.
The guidance is for symptom tracking and care reminders only. Medical decisions
must come from qualified healthcare professionals.
