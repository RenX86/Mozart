#!/usr/bin/env pwsh
# Mozart Docker Compose Manager
# Run this script from anywhere to manage your Mozart container

param(
    [Parameter(Position=0)]
    [ValidateSet("up", "down", "restart", "logs", "status", "build", "pull")]
    [string]$Action = "up"
)

# Set the directory where your docker-compose.yaml is located
# Uses the script's own directory to ensure it works regardless of where it's called from
$ComposeDir = "path to your docker-compose directory" # e.g. "C:\Mozart"

# Change to the compose directory
Push-Location $ComposeDir  

try {
    switch ($Action) {
        "up" {
            Write-Host "Starting Mozart..." -ForegroundColor Green
            docker compose up -d
            Write-Host "`nMozart is running at http://localhost:5000" -ForegroundColor Cyan
        }
        "down" {
            Write-Host "Stopping Mozart..." -ForegroundColor Yellow
            docker compose down
        }
        "restart" {
            Write-Host "Restarting Mozart..." -ForegroundColor Yellow
            docker compose restart
        }
        "logs" {
            Write-Host "Showing logs (Ctrl+C to exit)..." -ForegroundColor Cyan
            docker compose logs -f
        }
        "status" {
            Write-Host "Mozart Status:" -ForegroundColor Cyan
            docker compose ps
        }
        "build" {
            Write-Host "Building Mozart..." -ForegroundColor Green
            docker compose build
        }
        "pull" {
            Write-Host "Pulling latest image..." -ForegroundColor Green
            docker compose pull
        }
    }
} finally {
    # Return to original directory
    Pop-Location
}
