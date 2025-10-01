# Repository Guidelines

## Project Structure & Module Organization
Runtime code lives in `src/`: `server/http-server.ts` exposes the HTTP and streamable bridges, `client/mcp-client-manager.ts` negotiates stdio clients for legacy calls, `stream/` wraps long-lived stdio sessions for SSE, `config/config.ts` shapes environment input, and `utils/` houses logging and tunneling helpers. TypeScript builds emit to `dist/`; nothing under that directory is edited manually. Documentation assets stay in `readme/`, and logs generated at runtime belong under the project root but are not version-controlled. Add new features by extending existing modules or creating additional subfolders inside `src/` to keep responsibilities narrow.

## Build, Test, and Development Commands
`npm run build` compiles TypeScript into `dist/`. `npm start` runs the compiled server, while `npm run start:tunnel` enables Ngrok support for public URLs. For rapid iteration, prefer `npm run dev` or `npm run dev:tunnel`, which watch TypeScript sources and restart the Node process automatically. Run `npm run lint` to apply ESLint rules and `npm test` to execute the Jest suite via `ts-jest`.

## Coding Style & Naming Conventions
Write modern TypeScript using two-space indentation and strict compiler settings (see `tsconfig.json`). Use named exports where possible, camelCase for functions and variables, PascalCase for classes, and kebab-case for filenames such as `mcp-client-manager.ts`. Keep asynchronous flows on async/await and structure logs like `logger.info('Starting bridge', { port })` so metadata remains searchable. Run ESLint before commits to guarantee consistent style and safe imports.

## Testing Guidelines
Place unit tests in `src/__tests__/` or alongside modules as `*.spec.ts`. Mock external processes or network hops to keep tests deterministic. Cover both success and failure paths for new features, and avoid relying on Ngrok during unit tests. Use `npm test -- --watch` while iterating; confirm `npm test -- --coverage` meets the 80% statement target before requesting review.

## Commit & Pull Request Guidelines
Commits should stay small, present-tense, and descriptive (e.g., `fix log_level value`, `add tunnel shutdown guard`). Pull requests need a short problem statement, a summary of the solution, manual verification notes, and links to related issues. Include screenshots or sample curl output whenever API behavior changes, and wait for CI to pass before merging.

## Environment & Operations Notes
Store sensitive values in `.env`: `AUTH_TOKEN` secures all endpoints, `MCP_SERVERS` maps streamable routes (JSON object keyed by `serverId`), `ALLOWED_ORIGINS` locks requests to specific Origins, `STREAM_SESSION_TTL_MS` bounds idle SSE sessions, and `NGROK_AUTH_TOKEN` enables tunneling. Never commit `.env`; reference defaults in docs instead. When exposing the bridge remotely, prefer `npm run start:tunnel` and rotate Ngrok tokens routinely. Extend streamable behavior only through `src/stream/` so `StreamSessionManager` keeps cleanup logic and idle eviction consistent.
