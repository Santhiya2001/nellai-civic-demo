# Contributing

1. Open an issue describing a concrete bug or proposed module, without private data.
2. Fork the repository and create a focused branch.
3. Follow README setup. Keep secrets and runtime data out of commits.
4. Add reusable code, authorization checks and bounded request schemas.
5. For schema changes, add and test an Alembic revision. Do not edit a released migration.
6. Update documentation and the OpenAPI snapshot when interfaces change.
7. Run the backend tests, lint, web build and relevant browser tests.
8. Submit a pull request with the user-visible change, validation evidence and limitations.

Community extensions should follow [docs/module-development.md](docs/module-development.md). Avoid new core dependencies for an optional feature. Use semantic versioning and `/api/v1` compatibility. Contributions are under the MIT license.
