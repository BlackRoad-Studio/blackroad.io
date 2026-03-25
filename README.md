<!-- BlackRoad SEO Enhanced -->

# ulackroad.io

> Part of **[BlackRoad OS](https://blackroad.io)** — Sovereign Computing for Everyone

[![BlackRoad OS](https://img.shields.io/badge/BlackRoad-OS-ff1d6c?style=for-the-badge)](https://blackroad.io)
[![BlackRoad Forge](https://img.shields.io/badge/Org-BlackRoad-Forge-2979ff?style=for-the-badge)](https://github.com/BlackRoad-Forge)
[![License](https://img.shields.io/badge/License-Proprietary-f5a623?style=for-the-badge)](LICENSE)

**ulackroad.io** is part of the **BlackRoad OS** ecosystem — a sovereign, distributed operating system built on edge computing, local AI, and mesh networking by **BlackRoad OS, Inc.**

## About BlackRoad OS

BlackRoad OS is a sovereign computing platform that runs AI locally on your own hardware. No cloud dependencies. No API keys. No surveillance. Built by [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc), a Delaware C-Corp founded in 2025.

### Key Features
- **Local AI** — Run LLMs on Raspberry Pi, Hailo-8, and commodity hardware
- **Mesh Networking** — WireGuard VPN, NATS pub/sub, peer-to-peer communication
- **Edge Computing** — 52 TOPS of AI acceleration across a Pi fleet
- **Self-Hosted Everything** — Git, DNS, storage, CI/CD, chat — all sovereign
- **Zero Cloud Dependencies** — Your data stays on your hardware

### The BlackRoad Ecosystem
| Organization | Focus |
|---|---|
| [BlackRoad OS](https://github.com/BlackRoad-OS) | Core platform and applications |
| [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc) | Corporate and enterprise |
| [BlackRoad AI](https://github.com/BlackRoad-AI) | Artificial intelligence and ML |
| [BlackRoad Hardware](https://github.com/BlackRoad-Hardware) | Edge hardware and IoT |
| [BlackRoad Security](https://github.com/BlackRoad-Security) | Cybersecurity and auditing |
| [BlackRoad Quantum](https://github.com/BlackRoad-Quantum) | Quantum computing research |
| [BlackRoad Agents](https://github.com/BlackRoad-Agents) | Autonomous AI agents |
| [BlackRoad Network](https://github.com/BlackRoad-Network) | Mesh and distributed networking |
| [BlackRoad Education](https://github.com/BlackRoad-Education) | Learning and tutoring platforms |
| [BlackRoad Labs](https://github.com/BlackRoad-Labs) | Research and experiments |
| [BlackRoad Cloud](https://github.com/BlackRoad-Cloud) | Self-hosted cloud infrastructure |
| [BlackRoad Forge](https://github.com/BlackRoad-Forge) | Developer tools and utilities |

### Links
- **Website**: [blackroad.io](https://blackroad.io)
- **Documentation**: [docs.blackroad.io](https://docs.blackroad.io)
- **Chat**: [chat.blackroad.io](https://chat.blackroad.io)
- **Search**: [search.blackroad.io](https://search.blackroad.io)

---

# BlackRoad Static Site

This directory contains the static site served at **blackroad.io** via GitHub Pages.

## Contents

- `index.html` – Landing page with links to the AI chat and Composer Playground.
- `login.html` – Development login form accepting any non-empty credentials.
- `chat.html` – Placeholder for the Lucidia public-facing AI chat and terminal.
- `composer.html` – Placeholder for the Composer Playground.
- `dashboard.html` – Manual overview of site components and links.
- `status.html` – Manual system status page.
- `style.css` – Shared styling for all pages.
- `script.js` – Client-side login handler.
- `CNAME` – Configures the custom domain `blackroad.io` for GitHub Pages.

## Development

1. Clone the repository and ensure these files remain inside the `BlackRoad/` directory.
2. From this folder you can serve the site locally:

   ```bash
   cd BlackRoad
   python3 -m http.server 8000
   ```

   Then visit `http://localhost:8000` in your browser.

3. The `lucidia-agent.py` watcher automatically pushes changes in this directory to the `blackroad.io` repository. Ensure new files are added here so they are deployed.

## Deployment

The site is deployed on GitHub Pages. Pushing to the `blackroad.io` repository publishes the contents of this directory. The `CNAME` file tells GitHub Pages to serve the site at **blackroad.io**.

## Next Steps

- Replace the development login with real authentication.
- Implement the AI chat and terminal functionality.
- Build out the Composer Playground.
- Automate updates to the status page.

_Last updated on 2025-09-11_
