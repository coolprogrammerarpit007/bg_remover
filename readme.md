# FastAPI MySQL BG Remover Project

> A FastAPI project that removed background from the image

## 🚀 Features

- FastAPI backend
- MySQL database integration
- Automatic table creation using Alembic / SQLAlchemy models
- Environment variable-based configuration
- ***

## 📦 Prerequisites

Make sure you have the following installed:

- Python 3.10+
- MySQL Server & phpMyAdmin / MySQL Workbench
- pip / venv
- Git

---

## 🛠️ Project Setup (Local Environment)

### 1️⃣ Clone the Repository

```bash
 git clone <https://github.microprixs.in/microprixs/bg_remover.git>
 cd bg_remover/FastApi
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv .venv
```

### 3️⃣ Activate Virtual Environment

#### Windows

```
    windows
    .venv\Scripts\Activate.ps1
```

```bash
.venv\\Scripts\\activate
```

#### macOS / Linux

```bash
source .venv/bin/activate
```

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 5️⃣ Create MySQL Database

Open phpMyAdmin or MySQL shell:

```sql
CREATE DATABASE bgremoverdb;
```

> ✅ Only create the database — tables will be created automatically when FastAPI runs.

### 6️⃣ Create `.env` File

Create a `.env` file in the FastAPI folder:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=bgremoverdb
```

---

## ▶️ Run the Application

```bash
uvicorn main:app --reload
```

Backend runs at: `http://127.0.0.1:8000`
Swagger Docs: `http://127.0.0.1:8000/docs`

## ✅ Automatic Table Creation

- Tables are created on server start
- Make sure `models.py` and `Base.metadata.create_all(engine)` exist in project

---

## 🗂️ Folder Structure

```
FastApi/
 ├─ main.py
 ├─ models.py
 ├─ database.py
 ├─ routers/
 ├─ .env
 └─ requirements.txt
```

---

## 🔥 Notes

- Never push `.env` file to GitHub
- Use `requirements.txt` — do **not** commit `.venv`
- For production, use Docker + managed DB

---

## 🤝 Contributing

Feel free to fork and raise PRs

---

## 📄 License

MIT

---

### ✅ Now your FastAPI + MySQL AI project is ready to run locally 🎉

> For deployment guide (Render / Vercel / Railway) — ask anytime!
