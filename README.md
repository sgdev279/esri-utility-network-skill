# Esri Utility Network — Claude Skill + MCP Server

Expert knowledge of the **Esri ArcGIS Utility Network** for Claude and other AI agents, in two parts:

| Part | Folder | What it is |
|---|---|---|
| **Skill** | [`plugins/utility-network/skills/utility-network`](plugins/utility-network/skills/utility-network) | A Claude Agent Skill: 30+ reference files (concepts, administration, tracing, asset packages, dataset versions, licensing, REST, JavaScript SDK, Pro SDK C#, arcpy, Experience Builder, MCP), helper scripts, and evals |
| **MCP server** | [`mcp-server`](mcp-server) | `utility-network-mcp` — a Python MCP server that exposes trace, subnetwork, dirty-area and association tools over the UtilityNetworkServer REST API |

> Not affiliated with or endorsed by Esri. ArcGIS and ArcGIS Utility Network are trademarks of Esri. Reference content is paraphrased from public Esri documentation, with sources and review dates noted in each file.

## Install the skill

**Claude Code (plugin marketplace)**
```bash
claude plugin marketplace add YOUR_GITHUB_USER/esri-utility-network-skill
claude plugin install utility-network@esri-utility-network
```

**Claude.ai / Claude desktop app** — download `utility-network.skill` from the [latest release](../../releases/latest) and upload it where Claude lets you add skills (the file card also offers a Save skill button when shared in a chat).

**Any agent that reads skills from a folder** — copy `plugins/utility-network/skills/utility-network` into its skills directory (for Claude Code: `~/.claude/skills/utility-network`).

## Install the MCP server

```bash
pip install utility-network-mcp
```
Configuration and client setup: [`mcp-server/README.md`](mcp-server/README.md).

## What the skill covers

- Concepts: domain/structure networks, tiers, subnetworks, associations, terminals, network attributes, rules
- Operations: topology, dirty areas and the Status bitmask, Error Inspector, Update/Export Subnetwork, branch versioning
- Deployment: Foundations and asset packages, dataset versions 4–8 and the Pro/Enterprise compatibility matrix, Upgrade Dataset, publishing, ownership, licensing
- Development: REST (full trace configuration schema), JavaScript SDK, Pro SDK (C#), arcpy, Experience Builder
- AI agents: Esri's MCP betas, GP-task tools, and building a UN MCP server

## Repository layout

```
.claude-plugin/marketplace.json          # Claude Code marketplace catalog
plugins/utility-network/
  .claude-plugin/plugin.json             # plugin manifest
  skills/utility-network/                # the skill (SKILL.md, references/, scripts/, evals/)
mcp-server/
  pyproject.toml, server.json, src/      # PyPI package + MCP Registry metadata
.github/workflows/                       # CI + release
```

## Contributing

Issues and pull requests are welcome, especially corrections with a link to the Esri doc page and the ArcGIS version it applies to. Run `python plugins/utility-network/skills/utility-network/scripts/un_mcp_server.py --selftest` before submitting.

## License

MIT — see [LICENSE](LICENSE).
