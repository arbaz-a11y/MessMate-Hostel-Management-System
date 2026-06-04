# Hostel Mess Management System (Django + SQLite)

Goal: reduce food wastage by allowing students to mark meal absence or apply multi-day leave.

## Setup (macOS / Linux)

1. Create & activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies

```bash
pip install --upgrade pip
pip install django
```

3. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create an admin user (mess manager)

```bash
python manage.py createsuperuser
```

5. Start the server

```bash
python manage.py runserver
```

Open:

- Home: http://127.0.0.1:8000/
- Admin panel (built-in): http://127.0.0.1:8000/admin/
- Custom admin dashboard: http://127.0.0.1:8000/admin-panel/

## Sample Test Data (manual)

1. Signup a student from the UI: `Signup` (USN is the login ID).
2. Login as the student.
3. Submit:
   - A single meal absence for a date + meal.
   - A leave request (from date to date).
4. Login as admin (staff user) and visit `Admin Panel` / `Admin Dashboard`.

## Notes

- Login uses `USN` (stored as Django user's `username`).
- Duplicate meal absence for the same student/date/meal is blocked at both form and DB levels.
- Leave validation prevents `from_date > to_date`.

