# Phase 3: The API & Human Portal (React + Tailwind SPA)

> **Goal:** Build a headless REST API under `/api/` prefix, implement JWT authentication, and build a **React + Tailwind CSS SPA** that maintains full visual coherence with OpenOPC's native `office_ui`. The production build is served statically from FastAPI.

---

## APPROVED CONSTRAINTS
- **NO Streamlit.** React + Tailwind CSS only.
- **NO webhooks in V1.** Direct REST submission triggers resume.
- **Upload limits:** ≤5 files, ≤50MB total, ≤10MB per file.
- React SPA uses OpenOPC's design tokens (`--bg: #0c111b`, `--accent: #6366f1`, etc.)

---

## 3.1 — `shadow_adapter/security.py` (JWT & Auth)

**Standalone JWT system — no OpenOPC user management dependency.**

```python
class SecurityManager:
    def __init__(self, config: ShadowConfig)
    
    def hash_password(self, password: str) -> str
    def verify_password(self, plain: str, hashed: str) -> bool
    def create_access_token(self, contractor_id: str, username: str, roles: list[str]) -> str
    def decode_token(self, token: str) -> dict  # raises on invalid/expired
```

- bcrypt via `passlib` with auto-salt
- HS256 JWT with configurable secret and expiry
- First registered user gets `admin` role (bootstrap)

---

## 3.2 — `shadow_adapter/api/app.py` (FastAPI + Static Serving)

**Application factory pattern with SPA static file serving:**

```python
def create_app(config: ShadowConfig | None = None) -> FastAPI:
    app = FastAPI(title="Shadow Adapter API", version="0.1.0")
    
    # API routes under /api/ prefix
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])
    
    # Serve React production build as static files
    # Falls through to index.html for client-side routing
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="spa")
    
    return app
```

- Lifespan context manager for DB init/cleanup
- CORS middleware for dev mode (Vite proxy)
- `/api/health` endpoint for readiness probes

---

## 3.3 — `shadow_adapter/api/routes_auth.py`

| Route | Method | Auth | Request | Response |
|---|---|---|---|---|
| `/api/auth/login` | POST | None | `{"username", "password"}` | `{"access_token", "token_type", "expires_in", "contractor"}` |
| `/api/auth/register` | POST | Admin JWT | `{"username", "password", "email?", "display_name?"}` | `{"contractor", "message"}` |
| `/api/auth/me` | GET | JWT | — | `{"contractor"}` |

---

## 3.4 — `shadow_adapter/api/routes_tasks.py`

| Route | Method | Auth | Description |
|---|---|---|---|
| `/api/tasks` | GET | JWT | List tasks. Params: `status`, `assigned_to_me`, `limit`, `offset` |
| `/api/tasks/{id}` | GET | JWT | Full task detail + audit log |
| `/api/tasks/{id}/claim` | POST | JWT | Claim a pending task |
| `/api/tasks/{id}/unclaim` | POST | JWT | Release a claimed task |
| `/api/tasks/{id}/submit` | POST | JWT | Submit deliverable. **≤5 files, ≤50MB, ≤10MB/file**. Triggers resume. |
| `/api/tasks/{id}/audit` | GET | JWT | Audit trail |
| `/api/health` | GET | None | Health + pending count + version |

**Submit endpoint enforces all upload constraints:**
```python
@router.post("/{task_id}/submit")
async def submit_task(
    task_id: str,
    deliverable_text: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    ...
):
    if len(files) > 5:
        raise HTTPException(400, "Maximum 5 files per submission")
    # Validate each file: extension, size ≤10MB
    # Validate total: ≤50MB
    # Save files securely
    # Update shadow task → trigger resume pipeline
```

---

## 3.5 — React + Tailwind SPA (`shadow_adapter/frontend/`)

### Tech Stack

| Tool | Version | Notes |
|---|---|---|
| React | ^19.x | Matches OpenOPC's `office_ui` |
| Vite | ^7.x | Same build system |
| TypeScript | ^5.x | Same language |
| Tailwind CSS | ^4.x | Extended with OpenOPC design tokens |

### `tailwind.config.js` — OpenOPC Token Integration

```javascript
export default {
  content: ['./src/**/*.{ts,tsx}', './index.html'],
  theme: {
    extend: {
      colors: {
        'opc-bg': '#0c111b',
        'opc-elevated': '#141b2b',
        'opc-text': '#e2e8f0',
        'opc-text-secondary': '#8494a7',
        'opc-text-dim': '#64748b',
        'opc-accent': '#6366f1',
        'opc-accent-soft': 'rgba(99, 102, 241, 0.15)',
        'opc-border': 'rgba(148, 163, 184, 0.12)',
        'opc-surface': 'rgba(20, 27, 43, 0.7)',
        'opc-green': '#34d399',
        'opc-yellow': '#fbbf24',
        'opc-red': '#f87171',
        'opc-card': '#141b2b',
        'opc-secondary': '#1a2332',
      },
      borderRadius: {
        'opc': '12px',
        'opc-sm': '8px',
        'opc-xs': '6px',
      },
      fontFamily: {
        'sans': ['Inter', 'SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
    },
  },
}
```

### Pages

#### 1. **LoginPage** (`/login`)
- Dark background matching OpenOPC's `--bg`
- Centered card with accent-colored submit button
- Error display for invalid credentials
- JWT stored in `localStorage`, cleared on logout

#### 2. **DashboardPage** (`/`)
- 4 summary cards: Pending (yellow), Claimed (accent), Submitted (blue), Resumed (green)
- Recent activity feed
- Quick-claim button on pending tasks

#### 3. **TaskListPage** (`/tasks`)
- Filter tabs: All / Pending / My Tasks / Completed
- Cards with: title, role, priority badge, status badge, parked-at timestamp
- Click → TaskDetailPage

#### 4. **TaskDetailPage** (`/tasks/:id`)
- Full task description rendered as markdown
- OPC metadata panel (collapsible)
- **If pending:** "Claim" button
- **If claimed by me:** Submission form:
  - Rich text area for deliverable text
  - Drag-drop file upload (max 5 files, 10MB each)
  - File list with size, type, remove button
  - "Submit Deliverable" button with confirmation modal
- Audit trail timeline

### Components

| Component | Purpose |
|---|---|
| `Layout.tsx` | App shell: dark sidebar, top nav, content area. Matches OpenOPC's grid layout. |
| `TaskCard.tsx` | Card component for task list. Status badge, priority indicator, hover effects. |
| `TaskDetail.tsx` | Full task view with submission form. |
| `FileUpload.tsx` | Drag-drop zone. File validation (extension, size). Progress indicators. |
| `StatusBadge.tsx` | Colored pill badge: green/yellow/red/blue per status. |
| `ProtectedRoute.tsx` | Route guard — redirects to `/login` if no JWT. |

### API Client (`api/client.ts`)

```typescript
class ShadowAPIClient {
  private baseUrl: string;
  private getToken: () => string | null;

  async login(username: string, password: string): Promise<LoginResponse>;
  async getTasks(params?: TaskQueryParams): Promise<ShadowTask[]>;
  async getTask(id: string): Promise<ShadowTask>;
  async claimTask(id: string): Promise<void>;
  async submitTask(id: string, data: FormData): Promise<SubmitResponse>;
  
  // Auto-attaches JWT Bearer header
  // Auto-redirects to /login on 401
}
```

### Vite Dev Proxy

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    proxy: {
      '/api': 'http://localhost:8800',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
```

---

## 3.6 — Build & Serve Pipeline

```bash
# Development (two terminals):
cd shadow_adapter/frontend && npm run dev    # Vite dev server on :5173
shadow-serve --port 8800                      # FastAPI API on :8800

# Production:
cd shadow_adapter/frontend && npm run build   # → dist/
shadow-serve --port 8800                      # Serves both API + SPA
```

---

## Implementation Order

1. `security.py` — JWT & password hashing
2. `api/dependencies.py` — DI layer
3. `api/routes_auth.py` — Authentication endpoints
4. `api/routes_tasks.py` — Task endpoints with upload validation
5. `api/app.py` — Application factory + static serving
6. `frontend/` — React SPA scaffold (Vite + Tailwind + TypeScript)
7. Frontend pages: Login → Dashboard → TaskList → TaskDetail
8. Frontend components: Layout, TaskCard, FileUpload, StatusBadge
9. Integration test: full flow from login → claim → submit → verify resume
