#!/bin/bash

# One-command deploy script for DigitalOcean
# Run this from the project root on the server

set -e

echo "==> Pulling latest changes..."
git pull origin main

echo "==> Rebuilding and restarting services..."
docker-compose build api
docker-compose up -d

echo "==> Done! App running at http://$(curl -s ifconfig.me):8000"
