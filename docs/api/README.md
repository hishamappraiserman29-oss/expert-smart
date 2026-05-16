# API Reference

`openapi.yaml` is the canonical contract for the EXPERT_SMART HTTP API.

It covers the core report-workflow endpoints (`/api/valuation`, `/api/reports*`).
The full API surface (181 routes) is in `core_engine/bridge_api.py`.

## View as Swagger UI (locally)

```bash
docker run -p 8080:8080 \
  -e SWAGGER_JSON=/spec.yaml \
  -v "$(pwd)/docs/api/openapi.yaml:/spec.yaml" \
  swaggerapi/swagger-ui
# Visit http://localhost:8080
```

## Generate a client SDK

```bash
# Python client (example)
openapi-generator-cli generate \
  -i docs/api/openapi.yaml \
  -g python \
  -o client/python/
```

## Maintenance

Update this spec **with every change** to `bridge_api.py` endpoints, request/response
shapes, or component schemas. The `test_openapi_spec.py` test validates structure but
not semantics — manual review is still required when behaviour changes.

## Quick endpoint summary

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/valuation` | Generate Excel (+ optional PDF, persist, validate) |
| GET | `/api/reports` | List saved reports (filter by profile/status, paginate) |
| GET | `/api/reports/{id}` | Retrieve single report with full DTO |
| GET | `/api/reports/{id}/pdf` | Stream PDF for a saved report |
