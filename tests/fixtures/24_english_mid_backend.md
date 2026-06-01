# note-api

A RESTful API for managing personal notes with tagging and full-text search.

## Tech Stack

- **Runtime**: Node.js + Express
- **Database**: MongoDB + Mongoose
- **Auth**: JWT (access token + refresh token rotation)

## Getting Started

```bash
git clone https://github.com/user/note-api
cd note-api
npm install
cp .env.example .env   # fill in MONGODB_URI and JWT_SECRET
npm start
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Register new user |
| POST | /auth/login | Login, returns tokens |
| POST | /auth/refresh | Refresh access token |
| GET | /notes | Get all notes (paginated) |
| POST | /notes | Create note |
| PUT | /notes/:id | Update note |
| DELETE | /notes/:id | Delete note |
| GET | /notes/search?q= | Full-text search |

## Environment Variables

```
MONGODB_URI=mongodb://localhost:27017/noteapp
JWT_SECRET=your-secret-key
JWT_EXPIRES_IN=15m
REFRESH_TOKEN_EXPIRES_IN=7d
PORT=3000
```

## Running Tests

```bash
npm test
```
