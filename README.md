# Registre Cancer Backend

Backend API for the Registre Cancer platform, built with Django 6.0 and Django REST Framework. This service provides secure user authentication, patient record management, cancer registry workflows, GIS analytics, reporting, and multidisciplinary tumor board (RCP) support.

## 🚀 Project Overview

This repository contains the Django backend for the Registre Cancer application.
It exposes a REST API consumed by a separate frontend application, and is designed to run on PostgreSQL with deployment options like Render, Railway, or any containerized Python host.

Key responsibilities:
- Secure JWT authentication with custom user model and role-based access control
- Patient data management and cancer classification
- Audit logging for sensitive operations
- Geographic information system analytics for epidemiology
- Report generation and export
- Multidisciplinary committee (RCP) workflow management
- AI-powered patient extraction integration

## 🧩 Architecture

Main Django apps:
- `accounts` — authentication, JWT token management, user API, RBAC test endpoints, password reset
- `patients` — patient import, extraction endpoint, record CRUD, business logic
- `cancers` — cancer-related models and APIs
- `audit` — audit log viewset and security event tracking
- `gis_analytics` — geographic analysis, zones, communes, area layers, compare/analyze
- `reporting` — report generation APIs
- `rcp` — RCP session, participants, cases, decisions, protocols, templates
- `services/ai` — AI provider integration for extraction and automation

Supporting infrastructure:
- `config/` — Django settings, URL routes, WSGI/asgi entrypoints
- `media/` — uploaded files and generated assets
- `docs/` — deployment, testing, and auth architecture guides

## ⚙️ Technology Stack

- Python 3.11+ (3.14 tested in deployed environment)
- Django 6.0
- Django REST Framework
- Simple JWT (`djangorestframework-simplejwt`)
- PostgreSQL via `dj-database-url`
- `django-cors-headers`
- `whitenoise` for static file serving
- `gunicorn` for production WSGI
- `python-dotenv` for local environment variables

## 📦 Installation

```bash
cd Backend_registre_cancer
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file at the backend root with the required variables.

### Required environment variables

```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@host:port/dbname
ALLOWED_HOSTS=backend.example.com,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=https://frontend.example.com,http://localhost:5173
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=you@example.com
EMAIL_HOST_PASSWORD=secret
DEFAULT_FROM_EMAIL=no-reply@example.com
MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-small-latest
```

## 🧪 Database setup

```bash
python manage.py migrate
python manage.py createsuperuser
```

## 🚧 Running locally

```bash
python manage.py runserver
```

## 🔐 Authentication

The backend uses JWT authentication with refresh tokens.

Endpoints:
- `POST /api/accounts/login/` — obtain access and refresh tokens
- `POST /api/accounts/token/refresh/` — refresh access token
- `POST /api/accounts/logout/` — logout endpoint
- `POST /api/accounts/password-reset/` — request password reset
- `POST /api/accounts/password-reset-confirm/` — confirm reset

The frontend should send the access token with the `Authorization: Bearer <token>` header for protected requests.

## 🌐 Main API routes

- `GET /` — API health check
- `POST /api/extract-patient/` — AI-assisted patient extraction endpoint
- `api/accounts/` — user and auth endpoints
- `api/patients/` — patient record endpoints
- `api/cancers/` — cancer registry endpoints
- `api/gis/` — GIS analytics endpoints
- `api/reports/` — report generation and export endpoints
- `api/rcp/` — RCP workflow endpoints
- `api/audit/` — audit logs and security event endpoints

## 📄 Deployment

This backend is designed for production deployment with Gunicorn.

Example process:

```bash
gunicorn config.wsgi:application
```

On Render/Railway, define environment variables in the dashboard and ensure `DATABASE_URL` is set correctly.

### Deployment notes
- `DEBUG` must be `False` in production
- `ALLOWED_HOSTS` must include the deployed backend hostname
- `CORS_ALLOWED_ORIGINS` must include the frontend domain
- `whitenoise` is enabled for static asset serving

## 🧾 Testing

Run the Django test suite:

```bash
python manage.py test
```

For focused tests:

```bash
python manage.py test accounts
python manage.py test patients
python manage.py test cancers
```

## 📚 Documentation

The backend contains helpful guides in `docs/`:
- `docs/railway_deployment_guide.md`
- `docs/testing_guide.md`
- `docs/frontend_auth_architecture.md`


