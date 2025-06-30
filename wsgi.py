from app import app
from app import init_db

if __name__ == '__main__':
    try:
        with app.app_context():
            init_db()
        print("Starting ABB Store Management System...")
        print("Access the application at: http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Failed to start application: {str(e)}")
        print("Please check your database connection and configuration")