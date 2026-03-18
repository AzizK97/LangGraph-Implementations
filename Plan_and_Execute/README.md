# Plan and Execute (LangGraph + Redmine)

## Run with Docker (one command)

1. Set your credentials in `.env`:
   - `OPENROUTER_API_KEY`
   - `REDMINE_API_KEY`

2. Start the app:

```bash
docker compose up --build
```

You should see the interactive prompt:

- `You :` to ask questions
- `exit` to quit

## Run without Docker Compose

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set your credentials in `.env`:
   - `OPENROUTER_API_KEY`
   - `REDMINE_API_KEY`
   - `REDMINE_URL` (for local Redmine, `http://localhost:3000`)

4. Run the app:

```bash
python main.py
```

## Notes

- The container uses `REDMINE_URL=http://host.docker.internal:3000` so it can reach a Redmine server running on your host machine.
- If your Redmine is remote, update `REDMINE_URL` in `docker-compose.yml`.

## Stop and clean up

```bash
docker compose down
```
