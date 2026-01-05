# Backend - Database and CRUD

This folder contains a minimal SQLite-based backend implementing the database schema and CRUD helpers.

Files:

- [db.py](db.py): initializes SQLite database and tables.
- [crud.py](crud.py): functions to add, query, update and delete records.
- [smoke_test.py](smoke_test.py): small script that initializes the DB and runs example operations.

Quick start:

1. From the `/home/windowsuser/Desktop/projects/backend` directory, run:

```bash
python3 smoke_test.py
```

2. Inspect `data.db` (SQLite file) with any SQLite client if needed.

```bash
 python3 ./main_fixed.py --cert ./cert.pem --key ./key.pem
 ```