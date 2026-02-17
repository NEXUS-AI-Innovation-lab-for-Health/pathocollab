#!/bin/bash

echo "Stopping all Pixtral services..."

# Stop backend services
ports=(8001 8002 8003 8004 8005 3000)
for port in "${ports[@]}"; do
    pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo "Stopping service on port $port (PID: $pid)"
        kill -9 $pid
    fi
done

# Stop infrastructure
echo "Stopping infrastructure..."
cd infra
docker-compose -f docker-compose.dev.yml down
cd ..

echo "All services stopped!"
