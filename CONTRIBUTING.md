# Contributing to OpenOPC Shadow Adapter

Thank you for your interest in contributing to the **OpenOPC Shadow Adapter**! We welcome contributions, bug fixes, feature requests, and improvements.

---

## 🛠️ Local Development Setup

### 1. Prerequisites

- Python `>=3.10`
- Node.js `>=18` (for building the React Human Portal)
- `git`

### 2. Environment Setup

Clone the repository and set up a Python virtual environment:

```bash
git clone https://github.com/openopc/openopc-shadow-adapter.git
cd openopc-shadow-adapter

python3 -m venv venv
source venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

### 3. Running the Backend API Server

Set your development JWT secret and launch Uvicorn:

```bash
export SHADOW_JWT_SECRET="dev-secret-key-12345"
export SHADOW_LOG_LEVEL="DEBUG"

shadow-serve --port 8800
```

The API server will run at `http://localhost:8800`. You can inspect the OpenAPI documentation at `http://localhost:8800/docs`.

### 4. Running the Frontend (React + Vite)

Navigate to the frontend directory and install dependencies:

```bash
cd shadow_adapter/frontend
npm install
npm run dev
```

Vite will start the development server (typically at `http://localhost:5173`) and automatically proxy `/api` requests to `http://localhost:8800`.

To build the static production bundle served directly by FastAPI:

```bash
cd shadow_adapter/frontend
npm run build
```

The compiled assets will be placed in `shadow_adapter/frontend/dist/`.

---

## 🧪 Running Tests

Run the Pytest suite:

```bash
pytest tests/ -v
```

To run with coverage:

```bash
pytest --cov=shadow_adapter tests/
```

---

## 📝 Pull Request Guidelines

1. **Keep Zero Core Modifications:** Ensure your changes do not monkey-patch or modify OpenOPC core internals. Interactivity must flow through standard interfaces.
2. **Add Tests:** Any new features or bug fixes must include unit or integration tests in `tests/`.
3. **Follow Code Quality:** Run `typecheck` and ensure code formatting adheres to standard Python (PEP 8) and React/TypeScript standards.
4. **Documentation:** Update the `README.md` or phase docs if you add configuration options or change API endpoints.
