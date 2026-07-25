# Phase 5: Packaging & Documentation

> **Goal:** Finalize the README with foolproof installation instructions, provide a working `example_usage.py`, and ensure the package is pip-installable and production-ready.

---

## 5.1 — `README.md` (User-Facing Documentation)

**Sections:**
1. **Hero Banner & Badges** — Package name, Python version, license, OpenOPC compatibility
2. **What Is This?** — One-paragraph elevator pitch
3. **Architecture Overview** — Mermaid diagram of the intercept→park→resume flow
4. **Quick Start** (step-by-step):
   - Install the package
   - Set environment variables
   - Register the adapter in OpenOPC config
   - Start the shadow API server
   - Start the human portal
   - Run an OpenOPC task with `--agent shadow`
5. **Configuration Reference** — Full table of env vars with defaults
6. **API Reference** — Endpoint table with request/response examples
7. **Security** — JWT auth, upload security, and best practices
8. **Development** — How to run tests, contribute
9. **Extending** — How to add custom models, routes, UI components
10. **Troubleshooting** — Common issues and solutions
11. **License** — MIT

---

## 5.2 — `example_usage.py` (Drop-In Integration)

**What it demonstrates:**
1. Importing and registering `ShadowModeAdapter` into OpenOPC's adapter registry
2. Creating a task assigned to the shadow agent
3. Running the adapter's execute method (showing the park behavior)
4. Simulating a human submission
5. Showing the resume callback in action
6. Printing the full lifecycle report

```python
"""
example_usage.py — Drop-in integration of openopc-shadow-adapter with OpenOPC.

Run this script to see the full human-in-the-loop lifecycle:
  1. Task intercepted and parked
  2. Human submits deliverable (simulated)
  3. Result pushed back to OpenOPC
  4. DAG resumes

Usage:
    python example_usage.py

Prerequisites:
    pip install openopc-shadow-adapter
    export SHADOW_JWT_SECRET="your-secret-key"
"""
```

---

## 5.3 — `pyproject.toml` (Final Package Definition)

**Key Decisions:**
- `[project.scripts]`: `shadow-serve = "shadow_adapter.api.app:main"` 
- `[project.optional-dependencies]`:
  - `opc`: For adapter integration with OpenOPC
  - `ui`: For Streamlit portal
  - `dev`: For testing dependencies
  - `all`: Everything
- `[tool.pytest.ini_options]`: asyncio_mode = "auto"
- Classifiers: Development Status, Framework, License, Python versions

---

## 5.4 — `.env.example` (Environment Template)

```env
# Required
SHADOW_JWT_SECRET=change-me-to-a-secure-random-string

# Optional — defaults shown
SHADOW_DB_PATH=./shadow_tasks.db
SHADOW_UPLOAD_DIR=./shadow_uploads
SHADOW_MAX_UPLOAD_SIZE_MB=50
SHADOW_OPC_STORE_PATH=.opc/projects/default/store.db
SHADOW_API_PORT=8800
SHADOW_API_HOST=0.0.0.0
SHADOW_LOG_LEVEL=INFO
SHADOW_JWT_EXPIRE_HOURS=24
SHADOW_ALLOWED_EXTENSIONS=.pdf,.docx,.xlsx,.pptx,.txt,.md,.png,.jpg,.zip
```

---

## 5.5 — Future Extensibility Checklist

The package must be designed for these future extensions without breaking changes:

| Future Extension | How We Accommodate It |
|---|---|
| **Webhook callbacks** | `ShadowConfig.webhook_url` field (optional, unused now). Resume pipeline checks it. |
| **Multiple concurrent OpenOPC instances** | `opc_store_path` is per-config. Multiple adapter instances can run with different configs. |
| **Custom task types** | `extra_metadata: dict` on ShadowTask. API passes through unknown fields. |
| **Role-based access control** | `roles` field on ShadowContractor. `require_admin` dependency already exists. Add `require_role("reviewer")` pattern. |
| **Task priorities & SLAs** | `priority` and `deadline` fields already on ShadowTask. UI can sort/filter. |
| **Email notifications** | Plugin hook: `app.state.plugin_registry["on_task_parked"]` callback list. |
| **Database migration** | Schema version table in ShadowStore. `_ensure_schema()` runs migrations in order. |
| **React/Next.js portal** | API is headless REST. Any frontend can replace Streamlit. |
| **Kubernetes deployment** | No filesystem assumptions (configurable paths). Health endpoint for probes. |

---

## Implementation Order

1. Finalize `pyproject.toml` with all metadata and scripts
2. Write `README.md` 
3. Create `.env.example`
4. Write `example_usage.py`
5. Final review and test pass
