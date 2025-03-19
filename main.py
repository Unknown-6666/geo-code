from dashboard.app import app

@app.route('/health')
def health_check():
    """Health check endpoint for uptime monitoring"""
    return 'Bot is running', 200

# The app object is imported by gunicorn
# No need to run the app directly here since gunicorn will handle that