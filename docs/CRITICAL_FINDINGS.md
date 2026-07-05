# Aurika Critical Findings & Security Failures

## 1. Fake Production Databases (PostgreSQL / Redis)
- **Finding:** The deployment reports and security audits claim PostgreSQL encryption and a Redis database cluster. However, in `aurika_platform/storage/postgres_repo.py` and `aurika_platform/storage/redis_cache.py`, the storage adapters contain no database driver calls. Instead, they store data in local, ephemeral Python `dict` structures (`self._store` and `self._cache`).
- **Impact:** Any data written to "PostgreSQL" or "Redis" is immediately lost upon container restart. Multiple scaling nodes cannot share state.

## 2. Insecure JWT Verification Fallback (Authentication Bypass)
- **Finding:** In `aurika_platform/auth.py`, the `AuthManager` handles JWT authentication. If PyJWT is not installed, it falls back to parsing raw strings:
  ```python
  if token.startswith("mock_jwt_"):
      parts = token.split("_")
      return {"sub": parts[2], "role": parts[3]}
  ```
- **Impact:** An attacker can forge any admin credential without cryptography by submitting a token like `mock_jwt_anything_ADMIN`. Additionally, hardcoded admin keys (`aurika-admin-key-2026`) are committed directly to the codebase.

## 3. Client-Side Browser Simulation (Fake Live Dashboard)
- **Finding:** The dashboard WebSocket client (`wsClient.ts`) connects to `ws://localhost:8000/ws`. Because the backend lacks a WebSocket route, this connection fails. Upon failure, the script initiates `startMockFallback()` which spins up a browser interval loop generating fake, fluctuating telemetry data.
- **Impact:** The operator dashboard displays simulated guest counts, expected waits, and active tables generated on the client browser, masking the fact that the backend is disconnected.

## 4. LLM Directive Violation (Groq Llama-3.3 Integration)
- **Finding:** Phase 10 / Decision Engine explicitly stated: *"DO NOT build an LLM. DO NOT build a chatbot."* However, `query_agent.py` and `api/main.py` directly query Llama-3.3-70b-versatile via the Groq SDK to translate natural language inputs into SQLite queries.
- **Impact:** The system exposes an external API dependency on Groq, storing secrets in cleartext, and violating core architectural constraints.
