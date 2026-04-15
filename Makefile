.PHONY: dev backend frontend install clean start stop restart status logs

VENV := backend/venv/bin

dev: install
	@echo "Starting NEON COMMAND..."
	@echo "  Backend:  http://192.168.68.59:8000"
	@echo "  Frontend: http://192.168.68.59:3900"
	@trap 'kill 0' EXIT; \
	cd backend && ../$(VENV)/uvicorn main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && npx vite & \
	wait

backend:
	cd backend && ../$(VENV)/uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npx vite

install: $(VENV)/uvicorn
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install --silent

$(VENV)/uvicorn: backend/requirements.txt
	@echo "Setting up Python venv..."
	@test -d backend/venv || python3 -m venv backend/venv
	@$(VENV)/pip install -q -r backend/requirements.txt
	@touch $@

start: install
	@./scripts/neon-command.sh start

stop:
	@./scripts/neon-command.sh stop

restart: install
	@./scripts/neon-command.sh restart

status:
	@./scripts/neon-command.sh status

logs:
	@./scripts/neon-command.sh logs

clean:
	rm -rf frontend/node_modules frontend/dist backend/__pycache__ backend/venv
