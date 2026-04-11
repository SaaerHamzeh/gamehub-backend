# GameHub Backend - Mini ERP System

This is the server-side component of the GameHub Gaming Center Management System. Built with Django and Django REST Framework (DRF), it provides a robust, secure, and centralized authority for session management, dynamic resource configuration, and real-time cost calculation.

## Core Features

- **Backend-Authoritative Logic**: All session durations and costs are calculated strictly on the server to prevent frontend manipulation.
- **Dynamic Resource Configuration**: Supports any rentable resource (PCs, PlayStations, Billiards, Card Tables) with customizable metadata.
- **Role-Based Access Control (RBAC)**: Two-role system (`OWNER` and `STAFF`) with strictly enforced permissions.
- **Lazy Auto-End Mechanism**: Prepaid sessions are automatically terminated by the backend during active polling, eliminating the need for complex background workers for small-scale deployments.
- **Unified Settings Sync**: A dedicated bulk-sync API allows the React frontend to maintain parity with its local state logic while persisting to a real SQL database.

## Technical Stack

- **Framework**: Django 5.x
- **API**: Django REST Framework (DRF)
- **Authentication**: DRF Token Authentication
- **Database**: SQLite (Default) / PostgreSQL Ready
- **Security**: CORS Headers configured for secure frontend integration.

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd gamehub-backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

## API Documentation SUMMARY

| Endpoint | Method | Role Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/auth/login/` | POST | ALL | Returns a Token for authentication. |
| `/api/sessions/` | GET/POST | STAFF/OWNER | Manage gaming sessions. |
| `/api/settings/bulk-sync/` | POST | OWNER | Sync all devices and buffet items at once. |
| `/api/settings/devices/` | CRUD | OWNER | Manage resource types. |

---
Designed and developed for high-efficiency gaming center operations.
