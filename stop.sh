#!/usr/bin/env bash
echo "Sending shutdown signal to TelecomLens..."
if curl -s -X POST http://localhost:8000/api/shutdown > /dev/null 2>&1; then
    echo "Server stopped cleanly."
else
    echo "Server was not running (or already stopped)."
fi
