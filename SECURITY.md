# Security

## Reporting a vulnerability

If you find a security problem in the MCP server or scripts (for example a way to make a tool reach hosts it shouldn't, bypass the write confirmation, or leak credentials), please **don't open a public issue**. Use GitHub's private reporting: **Security → Report a vulnerability** on this repository. You'll get a response within 7 days.

## Using the MCP server safely

- Keep it **read-only** (the default) unless you need write tools, and then enable them only for trusted users.
- Use an account scoped to the one utility network service — never the utility network owner or a portal administrator.
- Keep credentials in environment variables or your MCP client's secret store; never commit them.
- Prefer OAuth app credentials or short-lived tokens over usernames and passwords.
- Log write operations (validate topology, update subnetwork) and run them against named versions where possible.

## Content

Never put passwords, tokens, internal service URLs, customer names or network data in issues, pull requests or the knowledge inbox. Maintainers will remove it and may need to rewrite history.
