# Legal Notice and Terms of Use

## Demonstration project

This is an unofficial, educational demonstration project showing how a modern
cadastral and land registry API could work. It is:

- **Shipped with a mock server** so that everything can be tested safely and offline.
  The default configuration, every example, every test and every page of the
  documentation target that mock server at `http://localhost:8000`.
- **Not an official tool** of any Croatian authority, and not affiliated with one.
- **Provided as is**, without warranty of any kind.

## Using it with another server

You may point the client, the CLI or the MCP server at another server, including
the official Croatian cadastre and land registry systems, on these conditions:

1. **Verify your rights first.** Before you use another server, verify that you
   have all the rights needed to use that server and the data it returns: its terms
   of service, the applicable data-protection law (real cadastral and land registry
   data is personal data), and any authorization the operator requires. This
   project neither grants nor obtains any such right for you.
2. **At your own risk.** You alone are responsible for how you use the software and
   the data you obtain with it, and for any consequence of that use.
3. **Respect the server.** Keep the rate limiting on, do not bypass authorization or
   access restrictions, and stop if the operator asks you to.
4. **Keep personal data out of the repository.** Raw responses from a real server
   contain names, addresses and tax numbers; the committed fixtures and mock data
   are redacted with `scripts/redact_capture.py`.

Nothing shown in the documentation is real property data.

## Default configuration

The client defaults to `CADASTRAL_API_BASE_URL=http://localhost:8000`, the address
of the included mock server. Change it only once you have done the checks above.

## License

The source code is released under the MIT License; see [LICENSE](../LICENSE). The
license covers the code only and grants no rights to any data held by the official
registers.
