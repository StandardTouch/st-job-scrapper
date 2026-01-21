#!/bin/bash

# Script to run the scrapper container, execute the script, and remove the container
# This is designed to be used with cron jobs

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure MySQL is running
if ! docker-compose ps mysql | grep -q "Up"; then
    echo "Starting MySQL container..."
    docker-compose up -d mysql
    echo "Waiting for MySQL to be healthy..."
    sleep 10
fi

# Run the scrapper container (it will execute the script and exit)
echo "Running scrapper container..."
docker-compose run --rm scrapper

echo "Scrapper execution completed. Container has been removed."
