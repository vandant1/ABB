#!/bin/bash

# ABB Store Management System - MySQL Setup Script
# This script helps set up the MySQL database for the application

echo "=========================================="
echo "ABB Store Management System - MySQL Setup"
echo "=========================================="

# Check if MySQL is installed
if ! command -v mysql &> /dev/null; then
    echo "❌ MySQL is not installed or not in PATH"
    echo "Please install MySQL first:"
    echo "  Ubuntu/Debian: sudo apt-get install mysql-server"
    echo "  CentOS/RHEL: sudo yum install mysql-server"
    echo "  macOS: brew install mysql"
    exit 1
fi

echo "✅ MySQL found"

# Check if database directory exists
if [ ! -d "database" ]; then
    echo "❌ Database directory not found"
    echo "Please ensure you're running this script from the project root directory"
    exit 1
fi

echo "✅ Database scripts found"

# Prompt for MySQL credentials
read -p "Enter MySQL root username (default: root): " MYSQL_ROOT_USER
MYSQL_ROOT_USER=${MYSQL_ROOT_USER:-root}

read -s -p "Enter MySQL root password: " MYSQL_ROOT_PASSWORD
echo

read -p "Enter application database username (default: abb_user): " APP_DB_USER
APP_DB_USER=${APP_DB_USER:-abb_user}

read -s -p "Enter application database password: " APP_DB_PASSWORD
echo

# Test MySQL connection
echo "Testing MySQL connection..."
mysql -u "$MYSQL_ROOT_USER" -p"$MYSQL_ROOT_PASSWORD" -e "SELECT VERSION();" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Failed to connect to MySQL"
    echo "Please check your credentials and ensure MySQL server is running"
    exit 1
fi

echo "✅ MySQL connection successful"

# Create application database user
echo "Creating application database user..."
mysql -u "$MYSQL_ROOT_USER" -p"$MYSQL_ROOT_PASSWORD" << EOF
CREATE USER IF NOT EXISTS '$APP_DB_USER'@'localhost' IDENTIFIED BY '$APP_DB_PASSWORD';
GRANT ALL PRIVILEGES ON abb_store_management.* TO '$APP_DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Database user created successfully"
else
    echo "❌ Failed to create database user"
    exit 1
fi

# Execute database scripts
echo "Executing database setup scripts..."

scripts=(
    "01_create_database.sql"
    "02_create_tables.sql"
    "03_create_views.sql"
    "04_create_procedures.sql"
    "05_create_triggers.sql"
    "06_seed_data.sql"
    "07_create_indexes.sql"
)

for script in "${scripts[@]}"; do
    echo "  Executing $script..."
    mysql -u "$MYSQL_ROOT_USER" -p"$MYSQL_ROOT_PASSWORD" < "database/$script"
    
    if [ $? -eq 0 ]; then
        echo "  ✅ $script executed successfully"
    else
        echo "  ❌ Failed to execute $script"
        exit 1
    fi
done

# Create .env file
echo "Creating .env configuration file..."
cat > .env << EOF
# MySQL Database Configuration for ABB Store Management System

# Database Connection
SQLALCHEMY_DATABASE_URI=mysql+pymysql://$APP_DB_USER:$APP_DB_PASSWORD@localhost:3306/abb_store_management

# MySQL Specific Settings
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=$APP_DB_USER
MYSQL_PASSWORD=$APP_DB_PASSWORD
MYSQL_DB=abb_store_management

# Application Configuration
SECRET_KEY=abb-store-management-super-secret-key-$(date +%s)
FLASK_ENV=development
FLASK_DEBUG=True

# Email Configuration (Optional - Update with your settings)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=True

# Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216

# Security Settings
WTF_CSRF_ENABLED=True
WTF_CSRF_TIME_LIMIT=3600
EOF

echo "✅ .env file created"

# Install Python dependencies
echo "Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    echo "⚠️  pip not found. Please install Python dependencies manually:"
    echo "   pip install -r requirements.txt"
fi

# Test database connection
echo "Testing database setup..."
python3 database_test.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Default login credentials:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo ""
    echo "To start the application:"
    echo "  python3 app.py"
    echo ""
    echo "Access the application at: http://localhost:5000"
else
    echo "❌ Database test failed. Please check the setup."
fi

echo "=========================================="
