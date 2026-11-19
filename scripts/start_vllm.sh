#!/bin/bash
nohup /home/23ucs603/btp/serve32.sh 6 8603 > /home/23ucs603/btp/serve32.log 2>&1 &
echo "Started vLLM PID: $!"
