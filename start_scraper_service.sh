#!/usr/bin/env bash
# ============================================================
# start_scraper_service.sh
# One-command pipeline:
# 1) Start Python scraper service
# 2) Start Java backend service
# 3) Call Java /api/interns/clean-job-documents
# 4) Print Java /api/interns/db/status
#
# Also supports service management commands.
#
# Usage:
#   bash start_scraper_service.sh run
#   bash start_scraper_service.sh            # same as run
#   bash start_scraper_service.sh run-scrape # optional: scrape + save
#
#   bash start_scraper_service.sh start
#   bash start_scraper_service.sh stop
#   bash start_scraper_service.sh restart
#   bash start_scraper_service.sh status
#   bash start_scraper_service.sh logs
#
# Optional finer-grained commands:
#   bash start_scraper_service.sh start-python
#   bash start_scraper_service.sh stop-python
#   bash start_scraper_service.sh start-java
#   bash start_scraper_service.sh stop-java
#   bash start_scraper_service.sh logs-python
#   bash start_scraper_service.sh logs-java
#
# Optional env vars:
#   SCRAPER_HOST=0.0.0.0
#   SCRAPER_PORT=8000
#   JAVA_BASE_URL=http://localhost:8080
#   CLEAN_MIN_LENGTH=50
#   CLEAN_LIMIT=0
# ============================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="$ROOT_DIR/Agent_data"
JAVA_DIR="$ROOT_DIR/backend/agent"
VENV_DIR="$ROOT_DIR/.venv"

HOST="${SCRAPER_HOST:-0.0.0.0}"
PORT="${SCRAPER_PORT:-8000}"
JAVA_BASE_URL="${JAVA_BASE_URL:-http://localhost:8080}"
JAVA_PORT_FROM_URL="${JAVA_BASE_URL##*:}"
JAVA_PORT="${JAVA_PORT_FROM_URL%%/*}"

if ! [[ "$JAVA_PORT" =~ ^[0-9]+$ ]]; then
  JAVA_PORT="8080"
fi

SCRAPER_PID_FILE="$ROOT_DIR/.scraper_service.pid"
SCRAPER_LOG_FILE="$ROOT_DIR/.scraper_service.log"
SCRAPER_HEALTH_URL="http://localhost:${PORT}/health"
PYTHON_CLEAN_DOCS_URL="http://localhost:${PORT}/api/v1/clean-job-documents"

JAVA_PID_FILE="$ROOT_DIR/.java_service.pid"
JAVA_LOG_FILE="$ROOT_DIR/.java_service.log"
JAVA_HEALTH_URL="${JAVA_BASE_URL}/api/interns/db/status"

JAVA_SCRAPE_SAVE_URL="${JAVA_BASE_URL}/api/interns/scrape-and-save"
JAVA_CLEAN_DOCS_URL="${JAVA_BASE_URL}/api/interns/clean-job-documents"
JAVA_DB_STATUS_URL="${JAVA_BASE_URL}/api/interns/db/status"
CLEAN_MIN_LENGTH="${CLEAN_MIN_LENGTH:-50}"
CLEAN_LIMIT="${CLEAN_LIMIT:-0}"

get_scraper_listener_pid() {
  lsof -ti tcp:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1
}

is_scraper_running() {
  local pid

  if [[ -f "$SCRAPER_PID_FILE" ]]; then
    pid="$(cat "$SCRAPER_PID_FILE")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi

  pid="$(get_scraper_listener_pid || true)"
  if [[ -n "$pid" ]]; then
    echo "$pid" > "$SCRAPER_PID_FILE"
    return 0
  fi

  return 1
}

is_java_running() {
  local pid

  if [[ -f "$JAVA_PID_FILE" ]]; then
    pid="$(cat "$JAVA_PID_FILE")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi

  pid="$(get_java_listener_pid || true)"
  if [[ -n "$pid" ]]; then
    echo "$pid" > "$JAVA_PID_FILE"
    return 0
  fi

  return 1
}

get_java_listener_pid() {
  lsof -ti tcp:"$JAVA_PORT" -sTCP:LISTEN 2>/dev/null | head -n 1
}

start_scraper_service() {
  if is_scraper_running; then
    echo "Python scraper is already running (PID $(cat "$SCRAPER_PID_FILE"))."
    return 0
  fi

  if [[ ! -d "$PYTHON_DIR" ]]; then
    echo "ERROR: Agent_data directory not found: $PYTHON_DIR"
    exit 1
  fi

  local existing_port_pid
  existing_port_pid="$(get_scraper_listener_pid || true)"
  if [[ -n "$existing_port_pid" ]]; then
    echo "Python scraper appears to be already listening on port ${PORT} (PID ${existing_port_pid})."
    echo "$existing_port_pid" > "$SCRAPER_PID_FILE"
    return 0
  fi

  echo "Starting scraper service on ${HOST}:${PORT}..."

  if [[ -d "$VENV_DIR" ]]; then
    nohup "$VENV_DIR/bin/uvicorn" main:app --app-dir "$PYTHON_DIR" --host "$HOST" --port "$PORT" >"$SCRAPER_LOG_FILE" 2>&1 &
  else
    echo "WARNING: .venv not found at $VENV_DIR, starting with system Python"
    nohup uvicorn main:app --app-dir "$PYTHON_DIR" --host "$HOST" --port "$PORT" >"$SCRAPER_LOG_FILE" 2>&1 &
  fi

  local pid=$!
  echo "$pid" > "$SCRAPER_PID_FILE"

  # Wait for health check (max 20s)
  for _ in $(seq 1 20); do
    if curl -sf "$SCRAPER_HEALTH_URL" >/dev/null 2>&1; then
      echo "Scraper service started successfully (PID $pid)."
      echo "Health: $SCRAPER_HEALTH_URL"
      echo "Logs:   $SCRAPER_LOG_FILE"
      return 0
    fi
    sleep 1
  done

  echo "ERROR: Scraper service failed to become healthy within 20 seconds."
  echo "Last log lines:"
  tail -n 30 "$SCRAPER_LOG_FILE" || true
  stop_scraper_service || true
  exit 1
}

start_java_service() {
  if is_java_running; then
    echo "Java backend is already running (PID $(cat "$JAVA_PID_FILE"))."
    return 0
  fi

  if [[ ! -d "$JAVA_DIR" ]]; then
    echo "ERROR: Java directory not found: $JAVA_DIR"
    exit 1
  fi

  if [[ ! -x "$JAVA_DIR/mvnw" ]]; then
    echo "ERROR: $JAVA_DIR/mvnw is not executable"
    exit 1
  fi

  local existing_port_pid
  existing_port_pid="$(get_java_listener_pid || true)"
  if [[ -n "$existing_port_pid" ]]; then
    echo "Java backend appears to be already listening on port ${JAVA_PORT} (PID ${existing_port_pid})."
    echo "$existing_port_pid" > "$JAVA_PID_FILE"
    return 0
  fi

  echo "Starting Java backend service..."
  nohup bash -lc "cd '$JAVA_DIR' && ./mvnw spring-boot:run" >"$JAVA_LOG_FILE" 2>&1 &

  local pid=$!
  echo "$pid" > "$JAVA_PID_FILE"

  # Wait for Java health check (max 120s)
  for _ in $(seq 1 120); do
    if curl -sf "$JAVA_HEALTH_URL" >/dev/null 2>&1; then
      echo "Java backend started successfully (PID $pid)."
      echo "Health: $JAVA_HEALTH_URL"
      echo "Logs:   $JAVA_LOG_FILE"
      return 0
    fi
    sleep 1
  done

  echo "ERROR: Java backend failed to become healthy within 120 seconds."
  echo "Last log lines:"
  tail -n 50 "$JAVA_LOG_FILE" || true
  stop_java_service || true
  exit 1
}

stop_scraper_service() {
  local pid=""
  local listener_pid=""

  if [[ -f "$SCRAPER_PID_FILE" ]]; then
    pid="$(cat "$SCRAPER_PID_FILE")"
  fi

  listener_pid="$(get_scraper_listener_pid || true)"

  if [[ -z "$pid" && -z "$listener_pid" ]]; then
    rm -f "$SCRAPER_PID_FILE"
    echo "Python scraper is not running."
    return 0
  fi

  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Stopping Python scraper (PID $pid)..."
    kill "$pid" 2>/dev/null || true
  fi

  if [[ -n "$listener_pid" ]] && [[ "$listener_pid" != "$pid" ]] && kill -0 "$listener_pid" 2>/dev/null; then
    echo "Stopping Python listener on port ${PORT} (PID $listener_pid)..."
    kill "$listener_pid" 2>/dev/null || true
  fi

  for _ in $(seq 1 10); do
    listener_pid="$(get_scraper_listener_pid || true)"
    if [[ -z "$listener_pid" ]]; then
      break
    fi
    sleep 1
  done

  listener_pid="$(get_scraper_listener_pid || true)"
  if [[ -n "$listener_pid" ]] && kill -0 "$listener_pid" 2>/dev/null; then
    echo "Force stopping Python listener on port ${PORT} (PID $listener_pid)..."
    kill -9 "$listener_pid" 2>/dev/null || true
  fi

  echo "Python scraper stopped."

  rm -f "$SCRAPER_PID_FILE"
}

stop_java_service() {
  local pid=""
  local listener_pid=""

  if [[ -f "$JAVA_PID_FILE" ]]; then
    pid="$(cat "$JAVA_PID_FILE")"
  fi

  listener_pid="$(get_java_listener_pid || true)"

  if [[ -z "$pid" && -z "$listener_pid" ]]; then
    rm -f "$JAVA_PID_FILE"
    echo "Java backend is not running."
    return 0
  fi

  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Stopping Java backend (PID $pid)..."
    kill "$pid" 2>/dev/null || true
  fi

  if [[ -n "$listener_pid" ]] && [[ "$listener_pid" != "$pid" ]] && kill -0 "$listener_pid" 2>/dev/null; then
    echo "Stopping Java listener on port ${JAVA_PORT} (PID $listener_pid)..."
    kill "$listener_pid" 2>/dev/null || true
  fi

  for _ in $(seq 1 20); do
    listener_pid="$(get_java_listener_pid || true)"
    if [[ -z "$listener_pid" ]]; then
      break
    fi
    sleep 1
  done

  listener_pid="$(get_java_listener_pid || true)"
  if [[ -n "$listener_pid" ]] && kill -0 "$listener_pid" 2>/dev/null; then
    echo "Force stopping Java listener on port ${JAVA_PORT} (PID $listener_pid)..."
    kill -9 "$listener_pid" 2>/dev/null || true
  fi

  echo "Java backend stopped."

  rm -f "$JAVA_PID_FILE"
}

status_services() {
  if is_scraper_running; then
    local pid
    pid="$(cat "$SCRAPER_PID_FILE")"
    echo "Python scraper: running (PID $pid)"
    echo "  Health URL: $SCRAPER_HEALTH_URL"
    if curl -sf "$SCRAPER_HEALTH_URL" >/dev/null 2>&1; then
      echo "  Health check: OK"
    else
      echo "  Health check: FAIL"
    fi
  else
    echo "Python scraper: not running"
  fi

  if is_java_running; then
    local pid
    pid="$(cat "$JAVA_PID_FILE")"
    echo "Java backend: running (PID $pid)"
    echo "  Health URL: $JAVA_HEALTH_URL"
    if curl -sf "$JAVA_HEALTH_URL" >/dev/null 2>&1; then
      echo "  Health check: OK"
    else
      echo "  Health check: FAIL"
    fi
  else
    echo "Java backend: not running"
  fi
}

show_scraper_logs() {
  if [[ -f "$SCRAPER_LOG_FILE" ]]; then
    tail -n 80 "$SCRAPER_LOG_FILE"
  else
    echo "No scraper log file found: $SCRAPER_LOG_FILE"
  fi
}

show_java_logs() {
  if [[ -f "$JAVA_LOG_FILE" ]]; then
    tail -n 80 "$JAVA_LOG_FILE"
  else
    echo "No Java log file found: $JAVA_LOG_FILE"
  fi
}

show_logs() {
  echo "========== Python scraper logs =========="
  show_scraper_logs
  echo ""
  echo "========== Java backend logs =========="
  show_java_logs
}

start_services() {
  start_scraper_service
  start_java_service
}

stop_services() {
  stop_java_service
  stop_scraper_service
}

restart_services() {
  stop_services
  start_services
}

ensure_services_running() {
  start_scraper_service
  start_java_service

  if ! curl -sf "$JAVA_DB_STATUS_URL" >/dev/null 2>&1; then
    echo "ERROR: Java backend is not reachable at ${JAVA_BASE_URL}."
    exit 1
  fi
}

check_python_clean_endpoint() {
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$PYTHON_CLEAN_DOCS_URL" \
    -H "Content-Type: application/json" \
    -d '{"documents":[{"job_id":"healthcheck","jd_raw_text":"x"}],"min_length":1}' || true)"

  [[ "$code" == "200" ]]
}

ensure_python_clean_endpoint_ready() {
  if check_python_clean_endpoint; then
    return 0
  fi

  echo "Python clean endpoint is not ready. Restarting Python scraper service..."
  stop_scraper_service || true
  start_scraper_service

  if ! check_python_clean_endpoint; then
    echo "ERROR: Python clean endpoint is still unavailable: $PYTHON_CLEAN_DOCS_URL"
    echo "Last Python log lines:"
    tail -n 40 "$SCRAPER_LOG_FILE" || true
    exit 1
  fi
}

print_json() {
  local payload="$1"
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$payload" | python3 -m json.tool 2>/dev/null || printf '%s\n' "$payload"
  else
    printf '%s\n' "$payload"
  fi
}

run_clean_pipeline() {
  local clean_resp
  local status_resp

  echo "[1/5] Ensure Python + Java services are running..."
  ensure_services_running

  echo "[2/5] Verify Python clean endpoint is available..."
  ensure_python_clean_endpoint_ready

  echo "[3/5] Call Java clean-job-documents (minLength=${CLEAN_MIN_LENGTH}, limit=${CLEAN_LIMIT})..."

  if ! clean_resp="$(curl -sS -f -X POST "${JAVA_CLEAN_DOCS_URL}?minLength=${CLEAN_MIN_LENGTH}&limit=${CLEAN_LIMIT}")"; then
    echo "ERROR: Failed to call ${JAVA_CLEAN_DOCS_URL}"
    exit 1
  fi

  echo "clean-job-documents response:"
  print_json "$clean_resp"

  echo "[4/5] Fetch database status..."
  if ! status_resp="$(curl -sS -f "$JAVA_DB_STATUS_URL")"; then
    echo "ERROR: Failed to fetch ${JAVA_DB_STATUS_URL}"
    exit 1
  fi

  echo "db status:"
  print_json "$status_resp"

  echo "[5/5] Done."
}

run_scrape_pipeline() {
  local scrape_resp
  local status_resp

  echo "[1/4] Ensure Python + Java services are running..."
  ensure_services_running

  echo "[2/4] Call Java scrape-and-save..."

  if ! scrape_resp="$(curl -sS -f -X POST "$JAVA_SCRAPE_SAVE_URL")"; then
    echo "ERROR: Failed to call ${JAVA_SCRAPE_SAVE_URL}"
    exit 1
  fi

  echo "scrape-and-save response:"
  print_json "$scrape_resp"

  echo "[3/4] Fetch database status..."
  if ! status_resp="$(curl -sS -f "$JAVA_DB_STATUS_URL")"; then
    echo "ERROR: Failed to fetch ${JAVA_DB_STATUS_URL}"
    exit 1
  fi

  echo "db status:"
  print_json "$status_resp"

  echo "[4/4] Done."
}

cmd="${1:-run}"
case "$cmd" in
  run)
    run_clean_pipeline
    ;;
  run-scrape)
    run_scrape_pipeline
    ;;
  start)
    start_services
    ;;
  stop)
    stop_services
    ;;
  restart)
    restart_services
    ;;
  status)
    status_services
    ;;
  logs)
    show_logs
    ;;
  start-python)
    start_scraper_service
    ;;
  stop-python)
    stop_scraper_service
    ;;
  start-java)
    start_java_service
    ;;
  stop-java)
    stop_java_service
    ;;
  logs-python)
    show_scraper_logs
    ;;
  logs-java)
    show_java_logs
    ;;
  *)
    echo "Unknown command: $cmd"
    echo "Usage: bash start_scraper_service.sh {run|run-scrape|start|stop|restart|status|logs|start-python|stop-python|start-java|stop-java|logs-python|logs-java}"
    exit 1
    ;;
esac
