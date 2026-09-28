# Utility Network — Worked Example: A Custom MCP Tool via GP Task Exposure (Deep Reference)
*Builds on: `mcp/01-mcp-and-utility-network.md` (the "Expose Custom GP Tasks as
Custom MCP Tools" mechanism). This file is a concrete, implementable template
— not just the concept — for the single strongest UN use case for this
pattern: outage isolation & customer impact assessment.*

## Why this is the right first use case to build

A good candidate for "custom GP task exposed as an MCP tool" has three
properties: (1) it's currently a **manual, GIS-analyst-dependent** task, (2)
the underlying UN capability already exists and just needs **orchestrating**,
not inventing, and (3) the natural-language framing is genuinely natural for
a **non-GIS persona** (dispatcher, call-center rep, field supervisor) rather
than something only a GIS analyst would ask. Outage isolation hits all three:
it maps directly onto the **Isolation trace type**
(`pro-help/05-tracing.md`) — a trace type Esri built specifically to answer
"what needs to be operated to isolate this section" — and the business
question ("what do I shut off, who's affected") is exactly what a dispatcher
already needs to answer today, manually, often by calling a GIS analyst.

## Architecture

```
Natural-language prompt ("there's a leak near meter 4521 on Oak St —
what do I shut off, and how many customers lose service?")
        │
        ▼
AI agent connected to the ArcGIS Enterprise MCP catalog endpoint
        │
        ├─ discovers the custom tool via its mcp-tagged title/description
        ├─ Get GP Task Definition           (learns parameter schema)
        ├─ resolves "meter 4521 on Oak St"  (Query Data / Find Address
        │   → a starting feature GlobalID    Candidates, or logic inside
        │                                    the tool itself)
        ▼
Submit GP Task: AssessOutageImpact   ← your custom, mcp-tagged GP service
        │
        ▼
Get GP Task Job Status               (poll — this runs two traces, so
        │                              async is the right default)
        ▼
JSON result → agent narrates it in plain language
```

## The GP script tool: `AssessOutageImpact`

### Parameters
| Parameter | Type | Notes |
|---|---|---|
| `starting_feature_id` | String (required) | GlobalID/asset ID of the reported problem feature. An address string can also be accepted and resolved to a network feature via a snap/search step inside the tool (or via a companion geocoding step the agent calls first). |
| `domain_network_name` | String (optional) | e.g. `"WaterDistribution"` — needed if the UN has multiple domain networks and the starting feature's domain isn't unambiguous. |
| `isolation_category` | String (optional, default `"Isolation"`) | The network category marking isolating/protective devices in this org's configuration (`pro-help/03-*.md` — network categories are org-specific). |
| `customer_asset_types` | String[] (optional, default `["Service Point","Meter"]`) | Which asset types count as "a customer" for impact counting — varies by domain network. |

### Internal logic (two ordinary UN traces, nothing novel)
1. **Isolation trace** from `starting_feature_id`:
   ```python
   # via arcpy.un.Trace GP tool, or the equivalent REST/JS/C# call —
   # see pro-help/05-tracing.md for full parameter semantics
   isolation_result = arcpy.un.Trace(
       in_utility_network=UN_PATH,
       trace_type="ISOLATION",
       starting_points=[starting_feature_id],
       domain_network=domain_network_name,
       # category-based condition barrier restricting to isolation_category
   )
   isolating_devices = extract_isolating_features(isolation_result)
   ```
2. **Downstream/connected trace**, scoped to the isolated section, filtered
   by an **Output Asset Types** filter (`pro-help/05-tracing.md`) matching
   `customer_asset_types`:
   ```python
   impact_result = arcpy.un.Trace(
       in_utility_network=UN_PATH,
       trace_type="DOWNSTREAM",  # or CONNECTED, depending on domain network flow direction
       starting_points=isolating_devices,   # or the original starting_feature_id,
                                              # bounded by the isolation result
       output_asset_types=customer_asset_types,
   )
   affected_customers = extract_features(impact_result)
   ```
3. **Assemble a single JSON output** — GP services return this cleanly, and
   it's exactly the shape an LLM narrates well without needing to understand
   raw trace-result JSON (`pro-help/05-*.md`'s trace configuration schema,
   `js-api/04-*.md`'s `TraceResult` shape):
   ```json
   {
     "isolatingDevices": [
       { "assetType": "Gate Valve", "globalId": "{...}", "address": "123 Oak St", "action": "Close" }
     ],
     "affectedCustomerCount": 214,
     "affectedCustomers": [ { "accountId": "...", "address": "..." } ],
     "domainNetwork": "WaterDistribution",
     "traceMoment": "2026-06-29T14:32:00Z"
   }
   ```
   Cap `affectedCustomers` at a reasonable count (e.g. 50) with the true
   total still reported in `affectedCustomerCount` — an LLM response doesn't
   need (and shouldn't try to narrate) a 200-row customer list verbatim.

### Publishing and MCP registration
1. Publish `AssessOutageImpact` as a **geoprocessing service** — prefer
   **asynchronous** execution (`rest-api/06-asynchronous-operations-job-status.md`
   covers the general async-job reasoning that applies here too): two
   chained traces on a large network can genuinely take a while, and the
   MCP catalog's `Get GP Task Job Status` tool exists specifically to poll
   a job like this rather than block the agent's turn.
2. Tag the published item **`mcp`** (required — untagged items are invisible
   to the MCP catalog, per `mcp/01-*.md`'s "Prepare Your Data to Be
   MCP-Ready" step).
3. Write the title/description **for prompt-matching, not just humans** —
   this is the actual discovery mechanism, so phrase it the way a
   dispatcher would ask, not the way GIS staff would file it internally:
   > *"Outage Isolation & Customer Impact Assessment — given a reported
   > problem location in the network, identifies which valves/switches
   > must be operated to isolate the affected section and reports how many
   > customers are impacted. Use for questions like 'what do I need to
   > shut off near X' or 'how many customers are affected by the break at
   > Y.'"*

### What the end user experiences
> **Dispatcher**: "There's a water main break reported near meter 4521 on
> Oak Street. What do I need to shut off, and how many customers will lose
> service?"
>
> **Agent** (after resolving the starting feature, submitting the job,
> polling to completion): "Close these 2 valves: the gate valve at 118 Oak
> St and the gate valve at 145 Oak St. This will affect approximately 214
> customers along Oak St, Maple Ave, and Pine Ct."

No trace-type vocabulary, no barrier/category configuration, no raw JSON —
the GIS complexity is fully absorbed by the wrapped GP task, and the
person asking never needed to know the utility network's data model at all.

## Two smaller variants — same pattern, different trace, worth building next

### Load/demand summary tool
Wraps a connected/downstream trace with a **function barrier** summing a
load/demand network attribute (`pro-help/05-tracing.md`'s function-barrier
section; `pro-sdk/01-*.md`'s `FunctionResult`/`Add` pattern) — answers
planning questions like "how much load is on this transformer" or "how many
amps are downstream of this feeder" without anyone needing to hand-configure
a function barrier in Pro.

### Subnetwork health check tool
Wraps `validateNetworkTopology` (`rest-api/02-*.md`) and reads back
`discoveredSubnetworks` plus dirty-area status
(`pro-help/04-associations-editing-errors.md`'s Status bitmask) — answers
"is circuit 12 clean, and if not, what's wrong" as a single natural-language
question instead of an interactive Error Inspector session.

## Practical guidance for Claude

1. When someone wants to design a UN-to-MCP integration, **lead with
   picking the trace/operation type first** (isolation, downstream+function
   barrier, validate — per `pro-help/05-*.md` and `06-*.md`), then design
   the GP task around it — don't start from "what tool should I build"
   in the abstract.
2. Always design the **output as a compact, pre-summarized JSON object**,
   not raw trace results — the whole value of this pattern is that the GP
   task does the GIS-literate interpretation once, so the LLM (and the end
   user) never has to.
3. Default to **asynchronous** GP service execution for anything running
   more than one trace, and mention `Get GP Task Job Status` explicitly as
   the mechanism that makes this a non-issue for the calling agent.
4. Always mention the **`mcp` tag + discovery-oriented description**
   requirement — a perfectly good GP service is invisible to the MCP
   catalog without both.
