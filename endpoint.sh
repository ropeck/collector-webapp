#!/bin/bash
# make sure the times in crontab and at jobs are in Pacific time, not UTC
export TZ="America/Los_Angeles"

# run atd and cron in the background, tail the log output for the workload
touch /var/log/cron
touch /var/log/camera-collector

# Authenticate with Google Cloud using the service account key
if [ -f "/app/service-account-key.json" ]; then
  gcloud auth activate-service-account --key-file=/app/service-account-key.json
fi

# Set the default project (optional if your key file already contains the project ID)
gcloud config set project k8s-project-441922 --quiet
cd /app || exit


# start the web service on port 5000
# Use multiple workers to handle concurrent requests and prevent health check failures
# Increase timeout for video processing operations
gunicorn -w 2 --timeout 120 -b 0.0.0.0:5000 app:app
