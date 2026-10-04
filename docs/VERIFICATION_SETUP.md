# Groq source verification setup

1. Create a key in your Groq account at https://console.groq.com/keys.
2. Open your Vercel project → Settings → Environment Variables. Add GROQ_API_KEY for Production. Keep the value out of chat, Git and frontend code.
3. The default GROQ_VERIFICATION_MODEL is openai/gpt-oss-20b. It must support browser_search and strict structured outputs. groq/compound is decommissioned; it is not used.
4. Redeploy so the server receives the variable. Check /api/capabilities: verification.available should be true. This means configured, not proof that the key has quota or provider access. Submit one claim to verify actual connectivity.

The server first requires Groq browser_search, accepts sources from executed browser/search results, and then makes a separate schema-constrained Groq request using only retrieved excerpts. Missing evidence and provider failures never turn into false/true verdicts. Source links are filtered to retrieved public HTTP(S) URLs. Dates and entity matches still depend on AI interpretation; users should review citations.

The default combined flow evaluates a headline (first nonempty line, up to 400 characters) with the trained English Fakeddit model and examines the full submitted news text for claims. User source URL and publication date guide research; private notes and media are not sent to Groq. Input/page instructions are treated as untrusted data.

Verification is bounded to 50 seconds and five requests per client per worker per minute. This in-memory limit is not a distributed quota; production traffic additionally needs platform rate limits and Groq account spend limits. No data is persisted by this app. Groq/search-provider data handling applies to submitted claims.

Official API references: https://console.groq.com/docs/tool-use/built-in-tools/browser-search and https://console.groq.com/docs/structured-outputs.
