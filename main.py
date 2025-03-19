from dashboard.app import app

@app.route('/health')
def health_check():
    """Health check endpoint for uptime monitoring"""
    return 'Bot is running', 200

if __name__ == "__main__":
    # Use port 8080 instead since 5000 is in use
    app.run(host="0.0.0.0", port=8080, debug=True)