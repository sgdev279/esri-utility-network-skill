# utility-network-mcp

<!-- mcp-name: io.github.sgdev279/utility-network-mcp -->

An [MCP](https://modelcontextprotocol.io) server that lets AI assistants (Claude Desktop, Claude Code, VS Code, Cursor, and others) work with an **Esri ArcGIS Utility Network** published on ArcGIS Enterprise — run traces, find dirty subnetworks, summarise errors, and inspect associations through the `UtilityNetworkServer` REST API.

> Not affiliated with or endorsed by Esri. ArcGIS and ArcGIS Utility Network are trademarks of Esri.

## Tools

| Tool | Type | What it answers |
|---|---|---|
| `describe_network` | read | Domain networks, tiers, network attributes, categories, system layers |
| `list_trace_configurations` | read | Named trace configurations stored in the service |
| `trace` | read | Connected / upstream / downstream / subnetwork / isolation / shortest path / loops — returns a summary by asset group and type, not 100k raw elements |
| `query_associations` | read | Containment, attachment and connectivity associations for given features |
| `query_subnetworks` | read | Rows from the Subnetworks table (e.g. `ISDIRTY = 1`) |
| `dirty_area_summary` | read | Dirty areas grouped by Status, decoded into pending edits vs. real errors |
| `network_moments` | read | Whether topology is valid; when it was last enabled |
| `job_status` | read | Poll an async job |
| `validate_network_topology` | **write** | Only when `UN_ALLOW_WRITES=true`, and each call needs `confirm=true` |
| `update_subnetwork` | **write** | Same gating as above |

## Install

```bash
pip install utility-network-mcp      # or: uvx utility-network-mcp
utility-network-mcp --selftest        # offline checks
```

## Configure

| Variable | Required | Meaning |
|---|---|---|
| `UN_FEATURE_SERVICE_URL` | yes | `https://host/server/rest/services/<Service>/FeatureServer` |
| `UN_PORTAL_URL` | for login auth | Portal URL |
| `UN_CLIENT_ID` / `UN_CLIENT_SECRET` | option A | OAuth app (client credentials) |
| `UN_USERNAME` / `UN_PASSWORD` | option B | Portal login via generateToken (not for SAML-only portals) |
| `UN_TOKEN` | option C | Pre-issued token |
| `UN_DEFAULT_VERSION` | no | Default `sde.DEFAULT` |
| `UN_ALLOW_WRITES` | no | `true` registers the write tools |
| `UN_MAX_IDS` | no | Sample globalIds per group in summaries (default 25) |

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "utility-network": {
      "command": "uvx",
      "args": ["utility-network-mcp"],
      "env": {
        "UN_FEATURE_SERVICE_URL": "https://gis.example.com/server/rest/services/Electric/FeatureServer",
        "UN_PORTAL_URL": "https://gis.example.com/portal",
        "UN_CLIENT_ID": "...",
        "UN_CLIENT_SECRET": "..."
      }
    }
  }
}
```

## Requirements and licensing

- ArcGIS Enterprise with the utility network published as a feature service with the Utility Network capability (enterprise deployment; file/mobile geodatabase networks have no REST API).
- Read tools (query, trace) don't need the ArcGIS Advanced Editing user type extension. The write tools do.

## Safety

Read-only by default. Write tools need both the server switch and an explicit per-call confirmation, so the agent must ask a human first. Use an account scoped to the one service; never the utility network owner account.

## Design notes

See the companion skill's `references/mcp/03-building-a-utility-network-mcp-server.md` in this repository for the design, REST shapes, auth patterns and pitfalls.
