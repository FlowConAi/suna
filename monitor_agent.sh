#!/bin/bash
# Monitor agent startup

echo "=== Monitoring Agent Startup ==="
echo "1. Backend API logs:"
docker logs -f suna-backend-1 --tail 0 &
BACKEND_PID=$!

echo -e "\n2. Worker logs:"
docker logs -f suna-worker-1 --tail 0 &
WORKER_PID=$!

echo -e "\n3. RabbitMQ queue status:"
watch -n 2 'docker exec suna-rabbitmq-1 rabbitmqctl list_queues name messages consumers' &
RABBIT_PID=$!

echo -e "\nPress Ctrl+C to stop monitoring..."
wait

# Cleanup
kill $BACKEND_PID $WORKER_PID $RABBIT_PID 2>/dev/null