# Job Market Intelligence Tool

A real-world, end-to-end machine learning project that scrapes live job postings, cleans and stores the data in PostgreSQL, trains a salary prediction model, and serves predictions through a REST API.

---

## What It Does

Given a job title, location, and experience level — this tool predicts the expected salary range. It solves a real business problem: job seekers and hiring managers often have no idea if a salary is competitive. This tool answers that question using patterns learned from thousands of real job postings.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Scraping | Python, Selenium, BeautifulSoup |
| Data Cleaning | Pandas, Regex |
| Validation | Pydantic |
| Database | PostgreSQL, SQLAlchemy |
| Machine Learning | Scikit-learn, XGBoost |
| API | FastAPI, Uvicorn |
| Environment | Python-dotenv |

---

## Project Structure

```
job-market-intelligence-tool/
├── scraper/
│   ├── __init__.py
│   ├── scraper.py        # Selenium-based Indeed scraper
│   └── parser.py         # HTML parsing logic
├── data/
│   ├── __init__.py
│   └── cleaning.py       # Salary parsing, location normalization
├── db/
│   ├── __init__.py
│   └── database.py       # SQLAlchemy models + DB connection
├── ml/
│   ├── __init__.py
│   ├── features.py       # Feature engineering pipeline
│   └── train.py          # Model training + evaluation
├── api/
│   ├── __init__.py
│   └── main.py           # FastAPI endpoints
├── models/               # Saved .pkl model files
├── .env                  # Environment variables (not committed)
├── requirements.txt
└── README.md
```

---

## Database Schema

### `raw_postings`
Stores exactly what is scraped — zero processing. This is the source of truth.

| Column | Type | Description |
|---|---|---|
| id | SERIAL | Primary key |
| title | TEXT | Job title as scraped |
| company | TEXT | Company name as scraped |
| location | TEXT | Raw location string |
| salary_raw | TEXT | Raw salary string e.g. `"$80K - $100K a year"` |
| job_type | TEXT | Full-time, Part-time, Contract |
| url | TEXT UNIQUE | Job posting URL |
| indeed_job_id | TEXT UNIQUE | Indeed's internal job ID |
| scraped_at | TIMESTAMP | When the scraper collected this row |

### `clean_postings`
Processed, ML-ready version of raw data. Linked back to raw via foreign key.

| Column | Type | Description |
|---|---|---|
| id | SERIAL | Primary key |
| raw_id | INTEGER | Foreign key → raw_postings.id |
| title | TEXT | Normalized title |
| company | TEXT | Cleaned company name |
| location | TEXT | Standardized location |
| is_remote | BOOLEAN | Extracted from location string |
| is_hybrid | BOOLEAN | Extracted from location string |
| salary_min | FLOAT | Extracted minimum salary |
| salary_max | FLOAT | Extracted maximum salary |
| salary_mid | FLOAT | (min + max) / 2 — ML target variable |
| salary_type | TEXT | "annual" or "hourly" |
| experience_level | TEXT | "entry", "mid", or "senior" |
| job_type | TEXT | "full_time", "part_time", "contract" |
| cleaned_at | TIMESTAMP | When cleaning pipeline ran |

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/job-market-intelligence-tool.git
cd job-market-intelligence-tool
```

### 2. Create and activate virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the project root:
```
DATABASE_URL=postgresql://jobuser:yourpassword@localhost:5432/job_salary_tracker
```

### 5. Set up PostgreSQL
Create the user and database in PostgreSQL:
```sql
CREATE USER jobuser WITH PASSWORD 'yourpassword';
CREATE DATABASE job_salary_tracker OWNER jobuser;
GRANT ALL PRIVILEGES ON DATABASE job_salary_tracker TO jobuser;
```

### 6. Create database tables
```bash
python3 db/database.py
```

---

## Running the Project

### Step 1 — Scrape job postings
```bash
python3 scraper/scraper.py
```
Scrapes ~150 job postings from Indeed and stores raw data in PostgreSQL.

### Step 2 — Clean the data
```bash
python3 data/cleaning.py
```
Parses salary strings, normalizes locations, infers experience levels, populates `clean_postings` table.

### Step 3 — Train the model
```bash
python3 ml/train.py
```
Trains Linear Regression (baseline) and Random Forest models. Prints MAE and R² scores. Saves best model to `models/salary_model.pkl`.

### Step 4 — Start the API
```bash
uvicorn api.main:app --reload
```
API runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## API Endpoints

### `POST /predict`
Predict salary for a job posting.

**Request:**
```json
{
  "title": "Data Analyst",
  "location": "New York, NY",
  "is_remote": false,
  "experience_level": "mid"
}
```

**Response:**
```json
{
  "predicted_salary": 95000.00,
  "range_low": 83600.00,
  "range_high": 106400.00,
  "top_factors": ["experience_level", "location", "title_keywords"]
}
```

### `GET /jobs`
Search scraped job postings.

```
GET /jobs?title=data+analyst&min_salary=80000
```

### `GET /health`
Check API status.

```json
{ "status": "ok", "model": "random_forest_v1" }
```

---

## ML Pipeline

### Why Machine Learning?
Salary is determined by a combination of factors — title, location, seniority, job type — that interact in non-linear ways. A Random Forest model learns these patterns from thousands of real postings without being explicitly programmed with salary rules.

### Features Used
- Experience level (one-hot encoded)
- Location tier (NYC/SF = tier 2, Austin/Chicago = tier 1, other = tier 0)
- Remote/hybrid flag
- Job type
- TF-IDF features from job title (top 30 terms)

### Model Performance
| Model | MAE | R² |
|---|---|---|
| Linear Regression (baseline) | ~$18,000 | ~0.42 |
| Random Forest (final) | ~$11,000 | ~0.67 |

*Results vary based on scraped data volume and quality.*

---

## Why This Project Exists

This is a portfolio project built to demonstrate a complete, production-style ML workflow:

- Real data (not synthetic/Kaggle datasets)
- Proper data engineering (raw → clean separation)
- Reasoned feature engineering
- Honest model evaluation
- Deployable REST API

Built by Suman Acharya as part of an ML engineering learning path.

---

## Future Improvements

- Add full job description scraping for skill-level features
- Schedule scraper to re-run weekly with `schedule` library
- Add a `/retrain` endpoint that triggers retraining on fresh data
- Deploy with Docker
- Add a simple frontend dashboard