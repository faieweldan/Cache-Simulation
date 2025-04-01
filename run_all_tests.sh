#!/bin/bash

echo "🔍 Running all cache simulation tests..."

# Loop through all config files
for config in configs/*.cfg; do
  config_name=$(basename "$config" .cfg)

  # Loop through all input trace files
  for trace in inputs/*.txt; do
    trace_name=$(basename "$trace" .txt)

    # Construct expected output filename
    expected="outputs/${config_name}-${trace_name}.txt"

    # Run simulation and compare
    if diff <(python3 driver.py "$config" -t "$trace") "$expected" > /dev/null; then
      echo "✅ PASS: $config_name with $trace_name"
    else
      echo "❌ FAIL: $config_name with $trace_name"
    fi
  done
done
