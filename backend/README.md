# FastAPI Backend

A simple FastAPI backend application.

## Setup Instructions

### 1. Create Virtual Environment

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On Linux/Mac:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
# Development mode with auto-reload
fastapi dev
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/redoc

## Development

### Deactivate Virtual Environment

When you're done working on the project:

```bash
deactivate
```
