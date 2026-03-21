# MCP Onboarding

## Prinzip

- Nur teamweit notwendige MCP-Server in `.mcp.json`
- Persönliche Tests nicht committen
- Tokens nur über Environment Variablen einbinden

## Beispiel: projektweiter Remote-HTTP-Server

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${GITHUB_MCP_TOKEN}"
      }
    }
  }
}
```

## Beispiel: agent-spezifischer Browser-Testserver

Diesen nicht in `.mcp.json`, sondern direkt im Agent definieren:

```yaml
mcpServers:
  - playwright:
      type: stdio
      command: cmd
      args: ["/c", "npx", "-y", "@playwright/mcp@latest"]
```

## Beispiel: lokaler privater Testserver

Nicht committen. Per CLI lokal hinzufügen:

```powershell
claude mcp add --transport stdio --scope local my-test -- cmd /c npx -y @scope/my-mcp
```
