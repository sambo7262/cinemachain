.PHONY: rebuild up logs

# Force rebuild of both images from scratch (clears Docker layer cache).
# Use this when the running container appears to serve stale code.
rebuild:
	docker build --no-cache -t sambo7262/cinemachain-backend:latest ./backend
	docker push sambo7262/cinemachain-backend:latest
	docker build --no-cache -t sambo7262/cinemachain-frontend:latest ./frontend
	docker push sambo7262/cinemachain-frontend:latest
	docker compose up -d

# Start the stack (uses existing images — no rebuild)
up:
	docker compose up -d

# Tail logs for all services
logs:
	docker compose logs -f
