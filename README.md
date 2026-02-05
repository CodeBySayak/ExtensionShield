<h1 align="center">ExtensionShield</h1>

<p align="center">
  <strong>Enterprise Chrome Extension Security & Governance Platform</strong>
</p>

---

## Quick Start

### Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ExtensionShield.git
cd ExtensionShield

# 2. Configure environment
cp env.production.template .env
# Edit .env and add your OPENAI_API_KEY (required)

# 3. Build and run
docker compose up --build

# 4. Access the application
# → http://localhost:8007
```

### Local Development

```bash
# Install dependencies
make install                    # Python (uv sync)
cd frontend && npm install      # Frontend

# Configure frontend environment (for authentication)
cd frontend
# Create .env file with your Supabase credentials:
# VITE_SUPABASE_URL=https://your-project.supabase.co
# VITE_SUPABASE_ANON_KEY=your-anon-key
# Get these from: https://app.supabase.com/project/_/settings/api

# Start servers (two terminals)
make api                        # Terminal 1: API at http://localhost:8007
make frontend                   # Terminal 2: UI at http://localhost:5173
```

**Note**: If you see `placeholder.supabase.co` errors when trying to log in, you need to configure the frontend environment variables. See [Frontend Configuration](#frontend-configuration) below.

---

## Frontend Configuration

For authentication to work, you need to configure Supabase environment variables in the frontend:

1. **Get your Supabase credentials**:
   - Go to https://app.supabase.com
   - Select your project from the dashboard
   - Click **Settings** (gear icon) in the left sidebar
   - Click **API** under Project Settings
   - Copy the **Project URL** (e.g., `https://xxxxx.supabase.co`) → this is your `VITE_SUPABASE_URL`
   - Copy the **anon** or **public** key from the "Project API keys" section → this is your `VITE_SUPABASE_ANON_KEY`

2. **Create a `.env` file in the `frontend/` directory**:
   ```bash
   cd frontend
   cat > .env << EOF
   VITE_SUPABASE_URL=https://your-project-id.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key-here
   EOF
   ```

3. **Restart the frontend dev server** for changes to take effect.

**Important**: The `VITE_` prefix is required for Vite to expose these variables to the frontend code.

---

## Make Commands

```bash
make help           # Show all commands
make api            # Start API server
make frontend       # Start React dev server
make analyze URL=   # Analyze extension from URL
make test           # Run tests
make format         # Format code
make lint           # Lint code
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/GO_LIVE_CHECKLIST.md](docs/GO_LIVE_CHECKLIST.md) | **🚀 Step-by-step go-live checklist** |
| [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md) | Production deployment with Supabase |
| [docs/MIGRATIONS.md](docs/MIGRATIONS.md) | Supabase migrations runner and setup |
| [docs/analytics.md](docs/analytics.md) | Privacy-first analytics setup |
| [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md) | Product features, API reference, configuration |
| [docs/GOVERNANCE_ARCHITECTURE_AND_HLD.md](docs/GOVERNANCE_ARCHITECTURE_AND_HLD.md) | Architecture, data contracts, implementation details |
| [scripts/run_supabase_migrations.py](scripts/run_supabase_migrations.py) | Apply Supabase SQL migrations with tracking |
| [AGENTS.md](AGENTS.md) | AI/Agent coding guidelines |
| http://localhost:8007/docs | Interactive API documentation (when running) |

---

## Acknowledgments

**Note**: ExtensionShield is built on top of the **[ThreatXtension](https://github.com/barvhaim/ThreatXtension)** codebase and is under active solo development. I've taken the original extension-focused codebase and am building significant enhancements on top of it. My original custom rulesets remain private, but the modified code and enhanced privacy rulesets are public here.

This is a work in progress—thanks for your patience! For questions or issues: **snorzang65@gmail.com**

See [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) for detailed attribution and information about our enhancements over the ThreatXtension foundation.

## License

MIT License — see [LICENSE](LICENSE) for details.
