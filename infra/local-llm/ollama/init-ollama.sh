#!/bin/sh
set -eu

export OLLAMA_HOST="0.0.0.0:11434"

wait_for_ollama() {
  attempt=0
  until ollama list >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
      echo "Ollama API did not become ready in time."
      exit 1
    fi
    sleep 2
  done
}

render_modelfile() {
  src="$1"
  dest="$2"
  sed "s|{{BASE_MODEL}}|${OLLAMA_BASE_MODEL}|g" "$src" > "$dest"
}

ensure_base_model() {
  if ! ollama show "$OLLAMA_BASE_MODEL" >/dev/null 2>&1; then
    echo "Pulling base model $OLLAMA_BASE_MODEL ..."
    ollama pull "$OLLAMA_BASE_MODEL"
  fi
}

ensure_named_model() {
  model_name="$1"
  template_path="$2"
  temp_path="/tmp/${model_name}.Modelfile"

  render_modelfile "$template_path" "$temp_path"
  echo "Creating model alias $model_name ..."
  ollama create "$model_name" -f "$temp_path"

  rm -f "$temp_path"
}

ollama serve &
OLLAMA_PID=$!

trap 'kill "$OLLAMA_PID" 2>/dev/null || true' INT TERM EXIT

wait_for_ollama
ensure_base_model
ensure_named_model "${OLLAMA_EXTRACTOR_MODEL}" "/opt/ollama/models/extractor.Modelfile.template"
ensure_named_model "${OLLAMA_PLANNER_MODEL}" "/opt/ollama/models/planner.Modelfile.template"

echo "Ollama initialized successfully."

wait "$OLLAMA_PID"
