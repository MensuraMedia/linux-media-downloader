---
paths:
  - "src/api/**"
  - "src/server/**"
  - "src/routes/**"
  - "src/middleware/**"
  - "packages/backend/**"
  - "server/**"
  - "api/**"
---

# Backend / API Best Practices (Example Sector-Specific Rule)

> This is an EXAMPLE path-scoped rule for backend/API code. Copy and adapt it
> for your project's backend framework and language. This rule only loads when
> editing files matching the paths above.

## API Design
- Use consistent URL patterns: plural nouns, kebab-case (e.g., `/api/user-profiles`)
- Version APIs when breaking changes are unavoidable (`/api/v2/...`)
- Return standardized error responses: `{ code, message, details? }`
- Never leak stack traces, internal paths, or debug info to clients

## Input Validation
- Validate all external input at the API boundary (request body, query params, headers)
- Use schema validation (Zod, JSON Schema, Pydantic, or language-native equivalent)
- Reject unknown fields rather than silently ignoring them
- Sanitize string inputs to prevent injection

## Database
- Use parameterized queries — never string concatenation for SQL
- Wrap related operations in transactions
- Add indexes for frequently queried fields
- Log slow queries in development; set query timeouts in production

## Authentication & Authorization
- Verify auth on every request — never rely on client-side checks
- Use least-privilege: each endpoint should check specific permissions
- Rotate secrets and tokens on a schedule
- Rate-limit public and auth endpoints separately

## Error Handling
- Catch errors at the boundary; don't let unhandled exceptions reach clients
- Log errors with enough context to debug (request ID, user context, stack trace)
- Use appropriate HTTP status codes (400 for client errors, 500 for server errors)
- Distinguish between retryable and non-retryable errors

## Testing
- Integration tests for API endpoints (hit a real database when possible)
- Test error paths and edge cases, not just happy paths
- Load test critical endpoints before major releases
