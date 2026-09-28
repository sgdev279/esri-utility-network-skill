# Utility Network — Publishing, Ownership, Licensing & Permissions (Deep Reference)
*Sources: ArcGIS Pro Help FAQ and "Utility network dataset administration";
ArcGIS Server 11.5 "Utility Network services". Last reviewed: 2026-09-28.*

Covers who is allowed to do what, and what must be true before a utility
network can be published and used as services. Many "access denied",
"operation only allowed by the owner", and "tool is greyed out" questions
trace back to this file.

## Licensing (single source of truth for this skill)

| Need | Requirement |
|---|---|
| Any UN work in ArcGIS Pro (single-user or enterprise) | ArcGIS Pro **Standard or Advanced** |
| Enterprise: **create, publish, or edit** a utility network | Portal account with the **ArcGIS Advanced Editing user type extension** |
| Enterprise: **query and trace** | No user type extension needed |
| REST `validateNetworkTopology`, `updateSubnetwork`, `exportSubnetwork`, named trace configuration management | Advanced Editing user type extension |

There is no separate "Utility Network extension" license in Pro; older
material that mentions one is out of date. Scoping tip: read-only web apps,
MCP servers and dashboards that only trace or query can run under users
without the extension.

## The two owners

| Owner | What it is | Can it change? |
|---|---|---|
| **Database utility network owner** | The database user that created the network; part of the dataset's fully qualified name | No — only by recreating the data |
| **Portal utility network owner** | The portal account signed in to Pro when the network was created; stored as metadata | Yes — **Update Portal Dataset Owner** tool, run while signed in as the current portal owner. Afterwards, also transfer ownership of the related portal items (map, feature, map image layers). |

### Operations that need an owner

- Enable / disable network topology → **database owner**
- Upgrade Dataset → database owner connection (branch versioning) **and**
  portal owner sign-in
- Apply Asset Package → both owners, on DEFAULT
  (`08-asset-packages-foundations-migration.md`)
- Update subnetwork where it recreates diagrams → owner-level access
- Changing the portal owner → current portal owner

Symptom mapping:
- "Tool disabled/greyed out" or "must be the owner" → check which owner the
  operation needs and how the user is connected (database user *and* portal
  sign-in).
- "Operation is only allowed by the owner of the version" → that's
  **version** ownership (branch versions are private/protected/public),
  not network ownership. See `06-*.md`.

## Publishing prerequisites (enterprise deployment)

1. Data in an **enterprise geodatabase**, feature dataset **registered as
   branch versioned** (it can be nonversioned only during the initial
   direct-connection configuration phase).
2. Publisher signed in to the portal as the **portal utility network owner**,
   connected as the **database owner**.
3. Publish from a map containing the utility network layer and its
   classes, sharing as a web layer with **feature access** and the
   **Utility Network** and **Version Management** capabilities enabled
   (Network Diagram too if diagrams are used). The services work together:
   Utility Network (trace, subnetworks, topology), Network Diagram, Feature
   (edits/queries), Version Management (branch versions).
4. The database connection is registered with ArcGIS Server as a data store
   (by-reference publishing).
5. After publishing, enable topology (if not already) and validate.

After publishing, edits go through services. Direct database connections are
for the initial configuration/QA phase only.

## Roles checklist for common requests

| Request | Who / what they need |
|---|---|
| Web app user who traces | Portal user with view access to the layer; no extension |
| Field or web editor | Advanced Editing user type extension + edit privileges on the layer; named or default version access |
| Validate topology from a web app/script | Extension + edit access to the version being validated |
| Update subnetwork on DEFAULT | Extension; DEFAULT must be writable by that user (protected DEFAULT → owner/admin) |
| Admin tasks (enable topology, upgrade, apply asset package) | The database + portal owners, in a maintenance window |

## How to answer

- Name the exact license/role and the specific owner an operation needs;
  don't say "you need admin rights".
- For permission errors, identify which of the three is failing: license
  (user type extension), network ownership, or version ownership.
