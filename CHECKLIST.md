# Deployment Checklist

## Pre-Deployment Verification

### Code Quality
- [ ] **Backend**
  - [ ] All imports are resolvable (no missing dependencies)
  - [ ] Linting passes: `pylint backend/`
  - [ ] Unit tests pass: `pytest backend/`
  - [ ] No hardcoded secrets in code (check .env.example)
  - [ ] Error handling for all API endpoints
  - [ ] CORS origins configured (not `*` in production)

- [ ] **Frontend**
  - [ ] TypeScript compilation: `npm run build` succeeds
  - [ ] ESLint passes: `npm run lint`
  - [ ] No console errors in dev build
  - [ ] API URL uses environment variable (not hardcoded)
  - [ ] All page routes tested

### Security
- [ ] [ ] API endpoints require authentication (if needed)
- [ ] [ ] Database connection string uses secured credentials
- [ ] [ ] SECRET_KEY is strong random value
- [ ] [ ] HTTPS enabled in production (reverse proxy)
- [ ] [ ] CORS origins restricted to known domains
- [ ] [ ] No sensitive data in logs
- [ ] [ ] SQL injection prevention (using ORM, parameterized queries)
- [ ] [ ] XSS prevention (React auto-escapes, validate server-side)

### Database
- [ ] [ ] Database migrations tested on fresh instance
- [ ] [ ] Backup strategy defined (daily snapshots)
- [ ] [ ] Connection pooling configured
- [ ] [ ] Indexes created on frequently queried fields
- [ ] [ ] Database user has minimal permissions (read-only for read ops)

### Performance
- [ ] [ ] API response times < 200ms (measured with realistic data)
- [ ] [ ] Frontend bundle size < 500KB (gzipped)
- [ ] [ ] Database queries optimized (check query logs)
- [ ] [ ] Caching headers configured (ETags, Cache-Control)
- [ ] [ ] Static assets served from CDN (if applicable)

---

## Local Testing Environment

### Backend Testing
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run migrations (if using Alembic in future)
# flask db upgrade

# Run tests
pytest -v

# Performance test
time python -c "from planner_service import PlannerService; PlannerService.build_timetable(...)"

# Check dependencies
pip freeze
```

### Frontend Testing
```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Check size
ls -lh build/

# Test TypeScript compilation
npm run tsc --noEmit

# Security audit
npm audit
```

### Integration Testing
```bash
# Terminal 1: Start backend
export DATABASE_URL=sqlite:///test.db
python -m flask run --port=5000

# Terminal 2: Start frontend
npm start

# Manual testing
# 1. Create a plan
# 2. Add institution details
# 3. Add 2-3 teachers and subjects
# 4. Generate timetable
# 5. Export CSV
# 6. Verify CSV contents
```

---

## Docker Deployment

### Image Building
```bash
# Build both images
docker-compose build

# Check image sizes
docker images | grep timetable

# Optimal size targets:
# - Backend: < 500MB
# - Frontend: < 500MB
```

### Local Docker Testing
```bash
# Start services
docker-compose up

# Verify services are healthy
docker-compose ps

# Check logs
docker-compose logs backend
docker-compose logs frontend

# Test API
curl http://localhost:5000/api/health

# Stop services
docker-compose down

# Clean up (remove volumes)
docker-compose down -v
```

### Production Docker Configuration

```yaml
# docker-compose.prod.yml (example)
version: '3.9'
services:
  backend:
    image: timetable-backend:1.0.0
    restart: always
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/db
      FLASK_ENV: production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  frontend:
    image: timetable-frontend:1.0.0
    restart: always
    environment:
      REACT_APP_API_URL: https://api.example.com
    
  postgres:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  reverse-proxy:  # e.g., nginx
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

---

## Cloud Platform Deployment

### AWS Deployment (Example)

**Option 1: EC2 + RDS**
```bash
# 1. Launch EC2 instance (Ubuntu 22.04)
# 2. Install Docker & Docker Compose
# 3. Clone repo
# 4. Create RDS PostgreSQL instance
# 5. Update docker-compose.yml with RDS endpoint
# 6. docker-compose up -d
# 7. Configure CloudFront CDN
# 8. Point Route 53 DNS
```

**Option 2: Elastic Beanstalk**
```bash
# 1. Install EB CLI: `brew install aws-elasticbeanstalk`
# 2. eb init timetable-app
# 3. eb create timetable-env
# 4. eb deploy
# 5. eb open
```

**Option 3: ECS Fargate (Recommended)**
```bash
# 1. Push images to ECR
# aws ecr create-repository --repository-name timetable-backend
# docker tag timetable-backend:latest $ECR_REPO_URI:latest
# docker push $ECR_REPO_URI:latest

# 2. Create ECS task definitions
# 3. Create ECS service
# 4. Configure load balancer (ALB)
# 5. Set up auto-scaling policies
```

### Google Cloud Deployment (GCP)

**Cloud Run (Simplest for stateless services)**
```bash
# Backend
gcloud run deploy timetable-backend \
  --source backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=$DATABASE_URL

# Frontend (Cloud Storage + CDN)
npm run build
gsutil -m cp -r build/* gs://timetable-frontend-bucket/
```

### Kubernetes Deployment (K8s)

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: timetable-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: timetable-backend:1.0.0
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        livenessProbe:
          httpGet:
            path: /api/health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10

# frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: timetable-frontend
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: frontend
        image: timetable-frontend:1.0.0
        ports:
        - containerPort: 3000

# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  selector:
    app: timetable-backend
  ports:
  - port: 80
    targetPort: 5000
  type: LoadBalancer
```

```bash
# Deploy
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f service.yaml

# Check status
kubectl get pods
kubectl get services
```

---

## Monitoring & Logging

### Backend Monitoring
```python
# Integrate monitoring (prometheus example)
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
request_latency = Histogram('request_latency_seconds', 'Request latency')

@app.before_request
def before_request():
    g.start = time.time()

@app.after_request
def after_request(response):
    request_count.inc()
    request_latency.observe(time.time() - g.start)
    return response
```

### Logging Configuration
```python
# backend/app.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### Frontend Error Tracking
```tsx
// Integrate Sentry or similar
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: process.env.REACT_APP_SENTRY_DSN,
  environment: process.env.NODE_ENV,
});
```

---

## Rollback Plan

### In case of production issues:

```bash
# 1. Quick rollback (keep previous image tag)
docker-compose -f docker-compose.prod.yml down
docker pull timetable-backend:1.0.0-previous
docker-compose -f docker-compose.prod.yml up -d

# 2. Database rollback (if schema changed)
# Restore from backup:
pg_restore -d timetable_db backup-timestamp.sql

# 3. Communication
# - Notify stakeholders
# - Post incident report
# - Document remediation steps
```

---

## Sign-Off Checklist

- [ ] **Backend Owner**: Code review + performance testing approved
- [ ] **Frontend Owner**: UI/UX review approved + accessibility tested
- [ ] **DevOps Owner**: Infrastructure + monitoring setup completed
- [ ] **Security**: Security audit passed (no vulnerabilities)
- [ ] **QA**: 20+ manual test cases passed
- [ ] **Product**: Feature acceptance + business requirements met
- [ ] **Legal/Compliance**: Data protection + regulatory requirements met

---

## Post-Deployment

### Day 1
- [ ] Monitor application logs for errors
- [ ] Verify all API endpoints responding
- [ ] Confirm database backups running
- [ ] User acceptance testing (UAT)

### Week 1
- [ ] Collect performance baseline metrics
- [ ] Gather user feedback
- [ ] Fix critical bugs
- [ ] Document deployment artifacts

### Ongoing
- [ ] Weekly security patches
- [ ] Monthly performance reviews
- [ ] Dependency updates (monthly)
- [ ] Backup integrity tests (monthly)
