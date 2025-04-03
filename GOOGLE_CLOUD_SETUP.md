# Running the Discord Bot on Google Cloud Platform

This guide explains how to set up your Discord bot to run reliably on Google Cloud Platform.

## Option 1: Google Cloud Compute Engine VM (Recommended for Beginners)

### Step 1: Create a GCP Account
1. Sign up for Google Cloud Platform (you get $300 free credits as a new user)
2. Create a new project

### Step 2: Set Up a VM Instance
1. Go to Compute Engine → VM instances → Create instance
2. Choose a small machine type (e2-micro is free tier eligible)
3. Select Ubuntu as the operating system
4. Allow HTTP/HTTPS traffic if you need the web dashboard
5. Create and start the VM

### Step 3: Connect to Your VM
1. Click the SSH button in the Google Cloud Console
2. Once connected, run the following commands to update your system and install basic dependencies:
   - Update system packages
   - Install Python, Git, and PostgreSQL

### Step 4: Clone Your Repository
1. Use Git to clone your repository
2. Navigate into the repository directory

### Step 5: Set Up Python Environment
1. Create a virtual environment
2. Activate the virtual environment
3. Install all required Python packages from the requirements.txt file

### Step 6: Set Up the Database
1. Create a PostgreSQL database for your bot
2. Create a database user
3. Grant privileges to the user
4. Set up your database connection string

### Step 7: Create Environment File
1. Create a .env file with your Discord token and other secrets
2. Make sure to include DATABASE_URL and GOOGLE_API

### Step 8: Create a Service to Keep the Bot Running
1. Create a systemd service file
2. Configure the service to restart automatically if it crashes
3. Enable the service to start on boot
4. Start the service

### Step 9: Monitor Your Bot
1. Use systemctl to check the status of your bot
2. Use journalctl to view logs if there are issues

## Option 2: Using Docker and Google Cloud Run (Advanced)

For a more modern, containerized approach:

1. Create a Dockerfile in your project
2. Create a requirements.txt file with all dependencies
3. Build the Docker image
4. Push the image to Google Container Registry
5. Deploy to Cloud Run with your environment variables

Note: For Cloud Run, you'll need to use a Cloud SQL instance instead of a local PostgreSQL database.

## Additional Tips

1. **Set up a firewall**: By default, GCP VMs have all incoming ports blocked except SSH. If you're running a web dashboard, make sure to open port 5000.

2. **Consider a static IP**: If you're using API services that require whitelisting, consider reserving a static IP for your VM.

3. **Set up monitoring**: Use Google Cloud Monitoring to keep track of your VM's health and receive alerts if it goes down.

4. **Backup regularly**: Take regular snapshots of your VM or use a tool like `cron` to backup your database.

5. **Use smaller VM instances**: e2-micro instances are included in the GCP free tier.

## Troubleshooting

- If your bot crashes, check the logs with journalctl
- If PostgreSQL fails to start, check its logs
- If you run into permission issues, make sure the service is running as the right user