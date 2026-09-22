# Archived procurement experiments

These scripts preserve earlier exploratory work. They are not current TenderWatch connectors or application entry points. The current sources are **PLACSP and Generalitat de Catalunya**, as defined in [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md).

- `placsp.py`: original PLACSP feed experiment, retained unchanged.
- `ted.py`: original TED API experiment from the previous project scope, retained unchanged for historical reference. TED is not a current TenderWatch ingestion source.

Both scripts make live requests when executed or imported. Do not import them into application code or tests. Their presence does not imply a supported connector or a future implementation commitment.

## Historical TED API notes

The following references and observation were moved from the old root README to preserve useful research context. They document the archived experiment, not the current project's source architecture.

Swagger:
https://api.ted.europa.eu/swagger-ui/index.html#/Search/search

Search:
https://docs.ted.europa.eu/api/latest/search.html

TED no define un único esquema JSON de “tender” para POST /v3/notices/search. Ese endpoint devuelve notices (anuncios), y el contenido de cada elemento depende de los campos que tú hayas pedido en fields.

Field parameters:
https://docs.ted.europa.eu/ODS/latest/reuse/field-list.html
