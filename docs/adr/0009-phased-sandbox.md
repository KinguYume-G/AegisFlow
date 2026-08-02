# ADR-0009 — Implement Sandbox in Two Phases

- **Status**: Accepted
- **Decision**:
  - M2：临时 Docker Container。
  - M5：k3s Ephemeral Job。
- **Security**: non-root、read-only FS、resource limit、no Docker socket、network policy、TTL cleanup。
