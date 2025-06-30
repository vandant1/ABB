# ABB Store Management System

A comprehensive warehouse and inventory management system designed specifically for ABB India Ltd. This professional-grade Flask application provides robust material tracking, request management, and reporting capabilities.

## Features

### Core Functionality
- **Material Management**: Add, edit, delete, and track materials with detailed information
- **Inventory Tracking**: Real-time stock levels with automatic low-stock alerts
- **Request Management**: Submit, approve, and track material requests with workflow
- **Transaction History**: Complete audit trail of all material movements
- **User Management**: Role-based access control (Admin, Manager, Staff)
- **Bulk Operations**: Excel import/export for efficient data management
- **Advanced Reporting**: Comprehensive analytics and reporting dashboard

### Technical Features
- **Responsive Design**: Modern Bootstrap-based UI that works on all devices
- **Security**: CSRF protection, secure password hashing, role-based permissions
- **Database**: SQLAlchemy ORM with support for SQLite, MySQL, PostgreSQL
- **Email Notifications**: Automated alerts for low stock and request updates
- **File Upload**: Secure file handling with validation
- **Error Handling**: Professional error pages and logging

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone or download the application files**

2. **Create a virtual environment**
   \`\`\`bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   \`\`\`

3. **Install dependencies**
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

4. **Configure environment variables**
   \`\`\`bash
   cp .env.example .env
   # Edit .env file with your configuration
   \`\`\`

5. **Initialize the database**
   \`\`\`bash
   python app.py
   \`\`\`

6. **Access the application**
   - Open your browser and go to `http://localhost:5000`
   - Default admin credentials: `admin` / `admin123`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | Auto-generated |
| `DATABASE_URL` | Database connection string | `sqlite:///abb_store.db` |
| `SMTP_SERVER` | Email server for notifications | `smtp.gmail.com` |
| `SMTP_USERNAME` | Email username | - |
| `SMTP_PASSWORD` | Email password | - |

### Database Setup

The application supports multiple database backends:

- **SQLite** (default): `sqlite:///abb_store.db`
- **MySQL**: `mysql://user:password@localhost/dbname`
- **PostgreSQL**: `postgresql://user:password@localhost/dbname`

## Usage

### User Roles

1. **Administrator**
   - Full system access
   - User management
   - System configuration
   - All material operations

2. **Manager**
   - Material management
   - Request approval/rejection
   - Reports and analytics
   - Bulk operations

3. **Staff**
   - View materials
   - Create requests
   - View own transactions
   - Basic dashboard access

### Key Workflows

1. **Material Management**
   - Add new materials with detailed information
   - Set minimum/maximum stock levels
   - Track locations and suppliers
   - Monitor stock values

2. **Request Process**
   - Staff submits material requests
   - Managers review and approve/reject
   - Approved requests can be issued
   - Complete audit trail maintained

3. **Inventory Control**
   - Automatic low-stock alerts
   - Email notifications to managers
   - Bulk import/export capabilities
   - Real-time stock tracking

## API Endpoints

The application provides several API endpoints for integration:

- `GET /api/material/<id>` - Get material details
- `GET /api/low-stock-check` - Trigger low stock alerts

## Security Features

- **Authentication**: Secure login with password hashing
- **Authorization**: Role-based access control
- **CSRF Protection**: All forms protected against CSRF attacks
- **Input Validation**: Comprehensive form validation
- **File Upload Security**: Secure file handling with type validation

## Deployment

### Production Deployment

1. **Set environment variables**
   \`\`\`bash
   export FLASK_ENV=production
   export SECRET_KEY=your-production-secret-key
   export DATABASE_URL=your-production-database-url
   \`\`\`

2. **Use a production WSGI server**
   \`\`\`bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   \`\`\`

3. **Configure reverse proxy** (nginx recommended)

4. **Set up SSL certificate** for HTTPS

### Docker Deployment

\`\`\`dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
\`\`\`

## Maintenance

### Database Backup
\`\`\`bash
# SQLite
cp abb_store.db abb_store_backup_$(date +%Y%m%d).db

# MySQL
mysqldump -u username -p database_name > backup.sql
\`\`\`

### Log Monitoring
- Application logs are written to the console
- Configure external logging service for production
- Monitor error rates and performance metrics

## Support

For technical support or questions:
- Check the application logs for error details
- Verify environment configuration
- Ensure database connectivity
- Contact system administrator

## License

This application is developed for ABB India Ltd. All rights reserved.

---

**ABB Store Management System v1.0**  
Professional warehouse management solution for ABB India Ltd.
