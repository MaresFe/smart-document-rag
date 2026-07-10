# REST API Design

## API Goal

The frontend will communicate with the backend through REST API endpoints.
The backend will handle file upload, document processing, chat messages, retrieval and source tracking.

---

## Document Endpoints

| Method   | Endpoint                       | Purpose                    | Success          |
| -------- | ------------------------------ | -------------------------- | ---------------- |
| `POST`   | `/api/documents`               | Upload a new document      | `201 Created`    |
| `GET`    | `/api/documents`               | List user documents        | `200 OK`         |
| `GET`    | `/api/documents/{document_id}` | Get document detail        | `200 OK`         |
| `DELETE` | `/api/documents/{document_id}` | Delete document and chunks | `204 No Content` |

---

## Chat Endpoints

| Method | Endpoint                                   | Purpose                               | Success       |
| ------ | ------------------------------------------ | ------------------------------------- | ------------- |
| `POST` | `/api/chat/sessions`                       | Create a new chat session             | `201 Created` |
| `GET`  | `/api/chat/sessions`                       | List chat sessions                    | `200 OK`      |
| `GET`  | `/api/chat/sessions/{session_id}/messages` | Get chat messages                     | `200 OK`      |
| `POST` | `/api/chat/sessions/{session_id}/messages` | Ask a question and generate an answer | `201 Created` |

---

## Source Endpoint

| Method | Endpoint                             | Purpose            | Success  |
| ------ | ------------------------------------ | ------------------ | -------- |
| `GET`  | `/api/messages/{message_id}/sources` | Get answer sources | `200 OK` |

---

## File Upload Validation

Uploaded files will be validated before processing.

| Check            | Description                                 |
| ---------------- | ------------------------------------------- |
| File size        | Reject files larger than the allowed limit. |
| Extension        | Allow only pdf, docx, txt, csv and xlsx.    |
| MIME type        | Check detected file content type.           |
| File readability | Test if the parser can read the file.       |
| Safe filename    | Store files with generated safe names.      |
| Error handling   | Mark failed files with status `failed`.     |

---

## Document Status Values

| Status       | Meaning                                            |
| ------------ | -------------------------------------------------- |
| `uploaded`   | File is uploaded but not processed yet.            |
| `processing` | Text extraction, chunking or embedding is running. |
| `ready`      | Document is ready for question-answering.          |
| `failed`     | Document could not be processed.                   |

---

## Example: Upload Document

### Request

`POST /api/documents`

Content type:

```text
multipart/form-data
```

Form data:

| Field  | Type | Description       |
| ------ | ---- | ----------------- |
| `file` | File | Uploaded document |

### Response

```json
{
  "id": "document_uuid",
  "original_filename": "contract.pdf",
  "file_type": "pdf",
  "status": "processing",
  "created_at": "2026-07-10T22:30:00"
}
```

---

## Example: List Documents

### Request

`GET /api/documents`

### Response

```json
[
  {
    "id": "document_uuid",
    "original_filename": "contract.pdf",
    "file_type": "pdf",
    "status": "ready",
    "created_at": "2026-07-10T22:30:00"
  }
]
```

---

## Example: Create Chat Session

### Request

`POST /api/chat/sessions`

Body:

```json
{
  "title": "Contract Analysis"
}
```

### Response

```json
{
  "id": "session_uuid",
  "title": "Contract Analysis",
  "created_at": "2026-07-10T22:35:00"
}
```

---

## Example: Ask Question

### Request

`POST /api/chat/sessions/{session_id}/messages`

Body:

```json
{
  "document_id": "document_uuid",
  "question": "What are the termination conditions in this contract?"
}
```

### Backend Flow

| Step | Description                                                |
| ---- | ---------------------------------------------------------- |
| 1    | Save user question in `chat_messages`.                     |
| 2    | Convert question into embedding.                           |
| 3    | Search similar chunks in `document_chunks` using pgvector. |
| 4    | Send selected chunks to LLM as context.                    |
| 5    | Save assistant answer in `chat_messages`.                  |
| 6    | Save used chunks in `message_sources`.                     |
| 7    | Return answer and sources to frontend.                     |

### Response

```json
{
  "message_id": "assistant_message_uuid",
  "answer": "The termination conditions are explained in the related sections of the document.",
  "sources": [
    {
      "document_name": "contract.pdf",
      "page_number": 4,
      "chunk_id": "chunk_uuid",
      "similarity_score": 0.84
    }
  ]
}
```

---

## Error Responses

| Case               | Status Code                 | Description                            |
| ------------------ | --------------------------- | -------------------------------------- |
| Invalid file type  | `400 Bad Request`           | Unsupported file format                |
| Unauthorized user  | `401 Unauthorized`          | User is not authenticated              |
| Forbidden access   | `403 Forbidden`             | User cannot access this resource       |
| Not found          | `404 Not Found`             | Document, session or message not found |
| File too large     | `413 Payload Too Large`     | File size limit exceeded               |
| Unprocessable file | `422 Unprocessable Entity`  | File could not be read or processed    |
| Server error       | `500 Internal Server Error` | Unexpected backend error               |

