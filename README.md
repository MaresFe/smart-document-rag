## Current Status

The project currently includes the initial backend and database setup.

Completed backend features:

- FastAPI backend structure
- PostgreSQL + pgvector Docker service
- SQLAlchemy models and Alembic migrations
- Document upload endpoint
- Document metadata storage in PostgreSQL
- Text extraction service layer
- Basic chunking service
- Chunk storage in `document_chunks`
- Swagger/OpenAPI documentation

Currently supported extraction flow:

- TXT files can be uploaded, read, chunked, and stored.
- CSV, XLSX, DOCX, and PDF parser layer has been prepared and will be tested/improved incrementally.

Next planned steps:

1. Improve file validation and error handling.
2. Test PDF, DOCX, CSV, and XLSX extraction with real files.
3. Add embedding generation for chunks.
4. Store embeddings in PostgreSQL using pgvector.
5. Add semantic search endpoint.
6. Add LLM-based question answering endpoint.
7. Build Turkish frontend interface.