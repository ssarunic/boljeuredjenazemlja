# Legal Notice and Terms of Use

## Demonstration project, not for production use

This is an unofficial, educational demonstration project showing how a modern
cadastral and land registry API could theoretically work. It is:

- **Not authorized** for use with Croatian government production systems.
- **Not intended** for accessing real cadastral or land registry data without proper
  legal authorization.
- **Only for educational purposes** and for demonstrating API design patterns.
- **Shipped with a mock server** so that everything can be tested safely and offline.

## Restrictions

Because of the sensitive nature of land ownership data and the terms of service of
the official Croatian systems:

1. This code must not be used against production Croatian cadastral or land registry
   systems.
2. Access to real cadastral data requires proper legal authorization, which this
   project neither provides nor helps to obtain.
3. Every example, test, and piece of documentation in this repository targets the
   included mock server at `http://localhost:8000`.
4. Nothing shown in the documentation is real property data.

## Default configuration

The client defaults to `CADASTRAL_API_BASE_URL=http://localhost:8000`, the address
of the included mock server. Do not change it to point at official systems.

## License

The source code is released under the MIT License; see [LICENSE](../LICENSE). The
license covers the code only and grants no rights to any data held by the official
registers.
