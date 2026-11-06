# Local Switch server (headless, no Console)

Uses the official standalone Compose file from the Switch repo
(`deploy/local/standalone-docker-compose.yml`, also published as
`ghcr.io/sandbox-quantum/standalone-compose`) with server image
`switch-core:0.31.0`.

```sh
git clone --depth 1 https://github.com/sandbox-quantum/switch
mkdir switch-server && cd switch-server
cp ../switch/deploy/local/standalone-docker-compose.yml docker-compose.yml
cp ../switch/.env.example .env
bash ../switch/deploy/local/generate-env-secrets.sh .env local   # random local secrets
sed -i 's|^SWITCH_VERSION=.*|SWITCH_VERSION=0.31.0|; s|^GATEWAY_ADMIN_EMAIL=.*|GATEWAY_ADMIN_EMAIL=admin@localhost.local|' .env
docker compose up -d                          # server + database
# add --profile collab for the bundled Mattermost, --profile gateway for the admin UI
curl http://localhost:8000/health             # {"status":"ok"}
```

`AGENT_REGISTRATION_TOKEN` in that `.env` is the deployment's bootstrap key;
put it in this project's `.env` as `SWITCH_REGISTRATION_KEY` (both files are
gitignored).

`docker-compose.hostnet.yml` here is only needed on hosts where containers on
a Docker bridge network cannot reach each other (as on our Linux build box):
it puts every service on the host network and moves the API to port 8010.
Use it as `docker compose -f docker-compose.yml -f docker-compose.hostnet.yml up -d`.
