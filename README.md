# SimpExtrac - Job Scraping Platform

A comprehensive job scraping platform built with Django, Celery, and modern web technologies for automated job data collection and management.

## 🚀 Features

- **Multi-platform Job Scraping**: Automated scraping from Indeed, Glassdoor, and other job sites
- **RESTful API**: Comprehensive API endpoints for data access and integration
- **Real-time Dashboard**: HTMX-powered interactive interface with live updates
- **Async Processing**: Celery + Redis for background task processing
- **Scheduled Jobs**: Automated scraping with configurable schedules
- **Company Intelligence**: Automatic company website and email extraction
- **Data Management**: Duplicate detection and intelligent data merging

## 🏗️ Architecture

```
SimpExtrac/
├── jobs/          # Core models + REST API + HTMX frontend
├── scraper/       # Selenium-based scraping logic
├── celery_tasks/  # Background processing + scheduling
├── templates/     # HTML templates
├── static/        # CSS, JS, assets
└── data/          # Scraped data storage
```

## 🛠️ Tech Stack

- **Backend**: Django 5.2.7, Django REST Framework
- **Database**: SQLite (easily configurable to PostgreSQL/MySQL)
- **Task Queue**: Celery 5.3.4 + Redis
- **Frontend**: HTMX 1.9.10 + Alpine.js
- **Scraping**: Selenium, BeautifulSoup4, Requests
- **Styling**: Modern CSS with Font Awesome icons

## ⚡ Quick Start

### Prerequisites
- Python 3.9+
- Redis (via Docker recommended)
- Git

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd SimpExtrac
```

2. **Create virtual environment**
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start Redis (Docker)**
```bash
docker run -d -p 6379:6379 --name redis redis:alpine
```

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Start development server**
```bash
python manage.py runserver
```

8. **Start Celery worker (new terminal)**
```bash
celery -A SimpExtrac worker --loglevel=info
```

## 📡 API Endpoints

### Core Data
- `GET /api/` - API root with comprehensive documentation
- `GET /api/jobs/` - List jobs with filtering and search
- `GET /api/companies/` - List companies with job counts
- `GET /api/jobs/stats/` - Job statistics and metrics

### Task Management
- `POST /celery/api/manual-scrape/` - Trigger manual scraping
- `GET /celery/api/job-status/{task_id}/` - Check task status
- `GET /celery/scheduled/` - Manage scheduled jobs

### Frontend Pages
- `/` - Interactive dashboard
- `/jobs/` - Job listings with HTMX filtering
- `/companies/` - Company directory
- `/scraper/` - Scraper control interface

## 🔧 Configuration

### Environment Variables
Create a `.env` file:
```bash
SECRET_KEY=your-secret-key
DEBUG=True
REDIS_URL=redis://localhost:6379/0
```

### Scraping Configuration
Configure scraping sources in `scraper/main.py`:
- Indeed scraping parameters
- Glassdoor integration
- Custom scraping rules

## 🤖 Automated Scraping

### Manual Scraping
```python
# Via API
POST /celery/api/manual-scrape/
{
    "job_title": "Python Developer",
    "location": "Remote",
    "sources": ["indeed", "glassdoor"],
    "max_jobs": 50
}
```

### Scheduled Jobs
- Configure recurring scraping jobs via Django admin
- Support for cron expressions
- Real-time progress tracking

## 📊 Features Showcase

### Backend Expertise
- **Clean Architecture**: Separation of concerns with dedicated apps
- **API Design**: RESTful endpoints with comprehensive documentation
- **Async Processing**: Celery integration for scalable task processing
- **Data Modeling**: Optimized Django models with proper relationships
- **Real-time Updates**: HTMX integration for reactive UI

### Scraping Capabilities
- **Multi-platform**: Indeed, Glassdoor, and extensible architecture
- **Intelligence**: Company website and email extraction
- **Duplicate Handling**: Smart data merging across sources
- **Error Handling**: Robust scraping with retry mechanisms

## 🧪 Testing

```bash
# Run tests
python manage.py test

# Run specific app tests
python manage.py test jobs
python manage.py test scraper
```

## 📈 Performance

- **Caching**: Redis-based session and data caching
- **Database**: Optimized queries with select_related/prefetch_related
- **Pagination**: Efficient pagination for large datasets
- **Background Tasks**: Non-blocking scraping operations

## 🚀 Deployment

### Docker (Recommended)
```bash
# Build and run
docker-compose up --build
```

### Traditional Deployment
- Configure production database (PostgreSQL recommended)
- Set up Redis in production
- Configure Celery workers
- Serve static files via nginx/Apache

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

Built with ❤️ for modern job scraping and data management.

---

**Tech Stack**: Django • REST API • Celery • Redis • HTMX • Selenium • Modern CSS