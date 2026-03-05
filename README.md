<div align="center">

  <img src="frontend/public/extension-shield-logo.svg" alt="ExtensionShield" width="98" height="98" />

  # ExtensionShield
</div>

**Chrome Extension Security Scanner & Governance Platform**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) · [Security](docs/SECURITY.md) · [Get Started](docs/GET_STARTED.md) · [Contribute](docs/CONTRIBUTING.md)

---

ExtensionShield scans Chrome extensions (from the Web Store or CRX/ZIP uploads), runs security and privacy analysis, and produces risk scores
and summary reports. The **core** (scanner, CLI, local analysis) is **MIT-licensed** and works without any cloud. Optional **cloud** features
(auth, history, team monitoring, community queue) are available via [ExtensionShield Cloud](https://extensionshield.com).

- **Security**: [SECURITY.md](docs/SECURITY.md) — Reporting vulnerabilities, secrets policy  
- **Open-core**: [OPEN_CORE_BOUNDARIES.md](docs/OPEN_CORE_BOUNDARIES.md) — What's OSS vs Cloud and how it's enforced  

---

## Quick start

Follow these steps in order. You need **two terminals** for running the app (one for the API, one for the frontend).

<details open>
<summary><strong>Step 1 — Clone and install dependencies</strong></summary>

Clone the repository and install backend (Python) and frontend (Node) dependencies.

```bash
git clone git@github.com:Stanzin7/ExtensionShield.git
```

```bash
cd ExtensionShield
```

```bash
make install
```
Installs Python dependencies (uv sync).

```bash
cd frontend && npm install
```
Installs frontend dependencies.

> **Tip**: Use your own fork URL if you cloned from a fork. Replace `Stanzin7/ExtensionShield` with your GitHub org or username.
</details>

<details>
<summary><strong>Step 2 — Configure environment</strong></summary>

Copy the example env files and add your API key for summary reports (OSS mode is the default).

```bash
cp .env.example .env
```
Edit `.env` and set `OPENAI_API_KEY` (needed for summary reports).

```bash
cp frontend/.env.example frontend/.env
```
No changes needed for OSS mode; adjust if using Cloud features.
</details>

<details>
<summary><strong>Step 3 — Run the application</strong></summary>

Start the **backend** and **frontend** in **two separate terminals**. Each command starts a long-running server.

**Terminal 1 — Backend API**

```bash
make api
```
API will be available at **http://localhost:8007**.

**Terminal 2 — Frontend UI**

```bash
make frontend
```
UI will be available at **http://localhost:5173**.

Open **http://localhost:5173** in your browser to use ExtensionShield.

> **Note**: Do not run `make api && make frontend` in a single terminal. The API runs until you stop it, so the frontend would never start. Use two terminals.
</details>

Full setup (Docker, CLI, Cloud mode, Make commands): **[GET_STARTED.md](docs/GET_STARTED.md)**.  
Deployment and dev scripts (Railway, Supabase, CSP): **[scripts/README.md](scripts/README.md)**.

---

## What ExtensionShield does

| Feature | Description |
|--------|-------------|
| **Scan** | Extensions from the Chrome Web Store or by uploading CRX/ZIP files |
| **Analyze** | Permissions, SAST, entropy, and optional VirusTotal integration |
| **Score** | Security and privacy risk with generated reports |
| **Summarize** | Written summary of findings (optional) |

In **OSS mode** (default) you get the full scanner, CLI, local SQLite storage, and report UI—no cloud required. **Cloud mode** adds auth, scan history, telemetry, and enterprise features; see [GET_STARTED.md#enabling-cloud-mode](docs/GET_STARTED.md#enabling-cloud-mode) and [OPEN_CORE_BOUNDARIES.md](docs/OPEN_CORE_BOUNDARIES.md).

---

## Documentation

| Document | Description |
|----------|-------------|
| [GET_STARTED.md](docs/GET_STARTED.md) | Setup, config, Docker, CLI, OSS vs Cloud, Make commands |
| [scripts/README.md](scripts/README.md) | What each script does and when to run it |
| [OPEN_CORE_BOUNDARIES.md](docs/OPEN_CORE_BOUNDARIES.md) | OSS vs Cloud; enforcement; configuration |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](docs/SECURITY.md) | Reporting vulnerabilities; secrets policy |
| [COMMERCIAL.md](docs/COMMERCIAL.md) | Commercial use (non-binding) |
| [TRADEMARK.md](docs/TRADEMARK.md) | Brand usage guidelines |
| [CODE_OF_CONDUCT.md](docs/CODE_OF_CONDUCT.md) | Community standards |
| [NOTICE](docs/NOTICE) | Third-party attributions |

---

## License & attribution

- **Core** (scanner, CLI, local analysis): **MIT** — see [LICENSE](LICENSE).  
- **Cloud** (auth, Supabase, telemetry admin, community queue, enterprise forms): **proprietary**, available via [ExtensionShield Cloud](https://extensionshield.com).  

Attribution: [NOTICE](docs/NOTICE). Brand: [TRADEMARK.md](docs/TRADEMARK.md). Commercial use: [COMMERCIAL.md](docs/COMMERCIAL.md) (non-binding).

---

## Community

We build ExtensionShield in the open so security tools stay transparent and inspectable. Feedback, issue reports, and small improvements (docs, tests, rule tweaks) are welcome. If it helps you or your organization, consider contributing a PR, sharing your use case, or supporting the project. We run open-source programs and internships when we can—community support helps keep that going.

**Acknowledgments**: ExtensionShield is our own design; we took inspiration from [ThreatXtension](https://github.com/barvhaim/ThreatXtension) in the same space (extension scanning, VirusTotal integration).
