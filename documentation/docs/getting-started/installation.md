# Installation Guide

This guide covers different ways to install and run Collexa for development and production environments.

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB free space
- **OS**: Linux, macOS, or Windows

### Software Dependencies
- **Node.js**: 18.0+ (for frontend)
- **Python**: 3.11+ (for backend)
- **PostgreSQL**: 14+ (database)
- **Git**: Latest version

## Installation Options

### Option 1: Docker (Recommended)

The fastest way to get started with all dependencies included.

```bash
# Clone the repository
git clone https://github.com/UretzkyZvi/collexa.git
cd collexa

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

**Services started:**
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Documentation: `http://localhost:3001`

### Option 2: Local Development

For active development with hot reloading.

#### 1. Database Setup

**Using Docker (easier):**
```bash
docker run --name collexa-postgres \
  -e POSTGRES_DB=collexa \
  -e POSTGRES_USER=collexa \
  -e POSTGRES_PASSWORD=collexa \
  -p 5432:5432 \
  -d postgres:15
```

**Using local PostgreSQL:**
```sql
CREATE DATABASE collexa;
CREATE USER collexa WITH PASSWORD 'collexa';
GRANT ALL PRIVILEGES ON DATABASE collexa TO collexa;
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install  # or npm install

# Set environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start the frontend
pnpm dev  # or npm run dev
```

### Option 3: Production Deployment

Production deployment guide coming soon.

## Environment Configuration

### Backend Environment Variables

Create `backend/.env`:

```bash
# Database
DATABASE_URL=postgresql://collexa:collexa@localhost:5432/collexa

# Authentication (Stack Auth)
STACK_AUTH_PROJECT_ID=your-project-id
STACK_AUTH_SECRET_KEY=your-secret-key

# Security
SECRET_KEY=your-secret-key-here
HMAC_SECRET=your-hmac-secret-here

# CORS
FRONTEND_URL=http://localhost:3000

# Optional: Observability
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

### Frontend Environment Variables

Create `frontend/.env.local`:

```bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Stack Auth
NEXT_PUBLIC_STACK_PROJECT_ID=your-project-id
NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY=your-client-key
```

## Database Setup

### Running Migrations

```bash
cd backend

# Check current migration status
alembic current

# Run all pending migrations
alembic upgrade head

# Create a new migration (if needed)
alembic revision --autogenerate -m "Description"
```

### Sample Data (Optional)

```bash
# Load sample agents and data
python scripts/seed_data.py
```

## Verification

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### 2. Check Frontend

Open `http://localhost:3000` in your browser. You should see the Collexa login page.

### 3. Check Database Connection

```bash
# From backend directory
python -c "from app.db.session import engine; print('Database connected!' if engine.connect() else 'Connection failed')"
```

## Development Tools

### Recommended VS Code Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode"
  ]
}
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Find process using port
lsof -i :8000  # or :3000

# Kill process
kill -9 <PID>
```

**Database connection failed**
- Verify PostgreSQL is running
- Check connection string in `.env`
- Ensure database and user exist

**Frontend build errors**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Python import errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Getting Help

- **Documentation**: Check other sections of this guide
- **GitHub Issues**: [Report bugs or ask questions](https://github.com/UretzkyZvi/collexa/issues)
- **Logs**: Check `docker-compose logs` or application logs for errors

---

**Next**: [First Agent Tutorial →](./first-agent.md)
