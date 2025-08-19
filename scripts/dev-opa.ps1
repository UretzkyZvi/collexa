# Development script to start OPA with policies
# Run from project root: .\scripts\dev-opa.ps1

Write-Host "Starting OPA with Collexa policies..." -ForegroundColor Green

# Check if Docker is running
try {
    docker version | Out-Null
} catch {
    Write-Host "Error: Docker is not running or not installed" -ForegroundColor Red
    exit 1
}

# Start OPA container
$OPA_CONTAINER = "collexa-opa-dev"

# Stop existing container if running
docker stop $OPA_CONTAINER 2>$null
docker rm $OPA_CONTAINER 2>$null

# Start new OPA container
docker run -d `
    --name $OPA_CONTAINER `
    -p 8181:8181 `
    -v "${PWD}/backend/policies:/policies:ro" `
    openpolicyagent/opa:latest-envoy `
    run --server --addr=0.0.0.0:8181 --set=decision_logs.console=true /policies

if ($LASTEXITCODE -eq 0) {
    Write-Host "OPA started successfully on http://localhost:8181" -ForegroundColor Green
    Write-Host "Health check: http://localhost:8181/health" -ForegroundColor Cyan
    Write-Host "Policy data: http://localhost:8181/v1/data" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To test policy evaluation:" -ForegroundColor Yellow
    Write-Host 'curl -X POST http://localhost:8181/v1/data/collexa/authz/invoke -H "Content-Type: application/json" -d "{\"input\":{\"user\":{\"id\":\"u1\"},\"org\":{\"id\":\"o1\"},\"agent\":{\"id\":\"agent-1\"},\"capability\":\"test_capability\"}}"'
} else {
    Write-Host "Failed to start OPA container" -ForegroundColor Red
    exit 1
}

# Wait a moment and check health
Start-Sleep -Seconds 2
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8181/health" -Method Get -TimeoutSec 5
    Write-Host "OPA health check: OK" -ForegroundColor Green
} catch {
    Write-Host "Warning: OPA health check failed - container may still be starting" -ForegroundColor Yellow
}
