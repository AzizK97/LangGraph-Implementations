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

## Notes

- The container uses `REDMINE_URL=http://host.docker.internal:3000` so it can reach a Redmine server running on your host machine.
- If your Redmine is remote, update `REDMINE_URL` in `docker-compose.yml`.

## Stop and clean up

```bash
docker compose down
```
