#!/bin/bash
echo "=== Concurrent TTS ==="
for i in 1 2 3 4; do
  curl -s -o /dev/null -w "req$i: http=%{http_code} time=%{time_total}s\n" "http://localhost:8082/api/tts?text=test$i&lang=en" &
done
wait
echo "=== Done ==="
