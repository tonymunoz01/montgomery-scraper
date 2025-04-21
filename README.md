# Foreclosure Scraper API

A FastAPI-based web service for scraping and managing foreclosure case data.

## Features

- Scrape foreclosure cases from public records
- Store case data in PostgreSQL database
- RESTful API endpoints for accessing case data
- Automatic reCAPTCHA solving using CapMonster
- Proper error handling and logging

## Project Structure

```
app/
├── api/
│   └── v1/
│       ├── endpoints/
│       │   └── cases.py
│       └── api.py
├── core/
│   ├── config.py
│   └── database.py
├── models/
├── schemas/
│   └── case.py
├── services/
│   └── scraper.py
├── utils/
│   ├── recaptcha.py
│   └── scraper.py
└── main.py
```

## Prerequisites

- Python 3.8+
- PostgreSQL
- CapMonster API key

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd foreclosure-scraper-api
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

5. Update the `.env` file with your configuration:
- Database credentials
- CapMonster API key
- reCAPTCHA settings
- Other configuration values

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

2. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

- `GET /api/v1/cases/` - Get all cases
- `GET /api/v1/cases/{case_id}` - Get a specific case
- `POST /api/v1/cases/scrape` - Scrape new cases

## Development

- The project uses FastAPI for the web framework
- PostgreSQL for data storage
- Pydantic for data validation
- Loguru for logging
- BeautifulSoup for web scraping

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 