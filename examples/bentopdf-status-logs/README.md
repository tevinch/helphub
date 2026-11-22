# Filter BentoPDF access logs by HTTP status

BentoPDF’s Docker health checks and successful page requests can fill the container log. This example keeps the official self-hosted BentoPDF image and configures nginx to omit only 2xx and 3xx request records. It keeps 4xx and 5xx access records and nginx errors.

## Run the example

Run this command in the directory containing the Dockerfile, Compose file, and nginx fragment.

```sh
docker compose up --build -d --wait
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). The Compose example binds the host port to loopback and retains a real HTTP health check.

Try a page, a redirect, and a missing path.

```sh
curl -s -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:3000/?status-log-page'
curl -s -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:3000/ua/?status-log-redirect'
curl -s -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:3000/status-log-missing'
docker compose logs bentopdf
```

Expect 200, 301, and 404 in that order. The log should include the `status-log-missing` request and omit the first two probes. Startup messages and other nginx diagnostic output can still appear.

## Use it in an existing Compose deployment

Put the Dockerfile and status fragment together in a directory and set `build` on your current BentoPDF service to that directory. Give the derived image a local name and keep your existing ports, health check, and environment settings. Compose rebuilds the image with `docker compose up --build -d`.

The base is the official `bentopdf-simple` v2.8.12 image, pinned to its multi-platform digest. The Dockerfile adds one include to nginx’s HTTP block. The existing entrypoint can still apply `PORT`, `DISABLE_IPV6`, and `ROBOTS_NOINDEX` at startup. Recreating the container preserves the logging setup. Remove the build setting and use the upstream image again to restore the stock access log. When upgrading the base, verify the new image’s nginx layout and repeat the request checks above. [BentoPDF Docker deployment guide](https://www.bentopdf.com/docs/self-hosting/docker)

The fragment uses nginx’s built-in conditional access logging. It configures the inherited access log explicitly on the same path the base image uses. The image ships that path to Docker’s standard log stream. [nginx access log documentation](https://nginx.org/en/docs/http/ngx_http_log_module.html)

## Optional coffee

If this example saved you time and you’d like to buy me a coffee, thank you. It’s entirely optional.

- **USDC / SOL · Solana** — `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base** — `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20)** — `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
