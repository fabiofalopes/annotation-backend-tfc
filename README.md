# Annotation Backend System

A flexible backend system for text annotation tasks, with chat disentanglement as the first supported use case.

## Features

- User authentication and authorization
- Project management
- CSV data import
- Chat message thread annotation
- Role-based access control (Admin/Annotator)
- RESTful API with FastAPI
- Async database operations with SQLAlchemy
- SQLite database (can be easily switched to PostgreSQL)

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration:
   ```env
   DATABASE_URL=sqlite+aiosqlite:///./annotation.db
   SECRET_KEY=your-secret-key-here
   FIRST_ADMIN_EMAIL=admin@example.com
   FIRST_ADMIN_PASSWORD=change-this-password
   ```

## Running the Server

Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Documentation

### Authentication

- `POST /auth/token` - Login and get access token
- `POST /auth/register` - Register new user
- `GET /auth/me` - Get current user info

### Admin Endpoints

- `GET /admin/users` - List all users
- `POST /admin/users` - Create new user
- `DELETE /admin/users/{user_id}` - Delete user
- `GET /admin/projects` - List all projects
- `POST /admin/projects` - Create new project
- `DELETE /admin/projects/{project_id}` - Delete project

### Project Endpoints

- `GET /projects` - List user's projects
- `GET /projects/{project_id}` - Get project details
- `POST /projects/{project_id}/assign/{user_id}` - Assign user to project
- `DELETE /projects/{project_id}/assign/{user_id}` - Remove user from project

### Chat Disentanglement Endpoints

- `GET /chat-disentanglement/containers/{container_id}/messages` - List messages
- `POST /chat-disentanglement/messages/{message_id}/thread` - Annotate thread
- `GET /chat-disentanglement/containers/{container_id}/threads` - Get thread annotations
- `POST /chat-disentanglement/import` - Import chat data from CSV

## Data Import Format

The CSV import expects the following columns (mapped through the API):
- `turn_id` - Unique identifier for each message
- `user_id` - User who sent the message
- `turn_text` - The message content
- Optional: `timestamp`, `reply_to_turn`

## Development

### Project Structure

```
annotation-backend/
├── app/
│   ├── api/
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── projects.py
│   │   └── chat_disentanglement.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── auth.py
│   └── main.py
├── tests/
├── requirements.txt
└── README.md
```

### Adding New Features

1. Add new models in `models.py`
2. Create corresponding schemas in `schemas.py`
3. Implement API endpoints in appropriate router
4. Update documentation

## License

MIT License 