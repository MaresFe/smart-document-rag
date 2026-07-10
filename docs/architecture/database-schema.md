# Database Schema Design

## Database Choice

The project will use **PostgreSQL + pgvector**.

PostgreSQL will store normal relational data such as documents, users, chats and messages.
pgvector will store embedding vectors and allow similarity search over document chunks.

---

## Main Tables

| Table             | Purpose                                                 |
| ----------------- | ------------------------------------------------------- |
| `users`           | Stores system users.                                    |
| `documents`       | Stores uploaded document metadata.                      |
| `document_chunks` | Stores extracted text chunks and embeddings.            |
| `chat_sessions`   | Stores chat sessions.                                   |
| `chat_messages`   | Stores user questions and assistant answers.            |
| `message_sources` | Connects assistant answers with the source chunks used. |

---

## users

| Column       | Type      | Description    |
| ------------ | --------- | -------------- |
| `id`         | UUID      | User ID        |
| `email`      | TEXT      | User email     |
| `full_name`  | TEXT      | User full name |
| `created_at` | TIMESTAMP | Creation time  |

---

## documents

| Column              | Type      | Description                         |
| ------------------- | --------- | ----------------------------------- |
| `id`                | UUID      | Document ID                         |
| `user_id`           | UUID      | Owner user ID                       |
| `original_filename` | TEXT      | Original uploaded file name         |
| `stored_filename`   | TEXT      | Safe generated file name            |
| `file_type`         | TEXT      | pdf, docx, txt, csv, xlsx           |
| `mime_type`         | TEXT      | Detected MIME type                  |
| `file_size`         | BIGINT    | File size in bytes                  |
| `storage_path`      | TEXT      | File storage path                   |
| `status`            | TEXT      | uploaded, processing, ready, failed |
| `error_message`     | TEXT      | Error message if processing fails   |
| `created_at`        | TIMESTAMP | Upload time                         |
| `updated_at`        | TIMESTAMP | Last update time                    |

---

## document_chunks

| Column        | Type      | Description                        |
| ------------- | --------- | ---------------------------------- |
| `id`          | UUID      | Chunk ID                           |
| `document_id` | UUID      | Related document ID                |
| `chunk_index` | INTEGER   | Order of the chunk in the document |
| `page_number` | INTEGER   | Page number for PDF files          |
| `content`     | TEXT      | Extracted chunk text               |
| `embedding`   | VECTOR    | Embedding vector                   |
| `metadata`    | JSONB     | Extra source information           |
| `created_at`  | TIMESTAMP | Creation time                      |

---

## chat_sessions

| Column       | Type      | Description     |
| ------------ | --------- | --------------- |
| `id`         | UUID      | Chat session ID |
| `user_id`    | UUID      | Owner user ID   |
| `title`      | TEXT      | Chat title      |
| `created_at` | TIMESTAMP | Creation time   |

---

## chat_messages

| Column       | Type      | Description          |
| ------------ | --------- | -------------------- |
| `id`         | UUID      | Message ID           |
| `session_id` | UUID      | Related chat session |
| `role`       | TEXT      | user or assistant    |
| `content`    | TEXT      | Message content      |
| `created_at` | TIMESTAMP | Message time         |

---

## message_sources

| Column             | Type  | Description                                 |
| ------------------ | ----- | ------------------------------------------- |
| `id`               | UUID  | Source relation ID                          |
| `message_id`       | UUID  | Assistant message ID                        |
| `chunk_id`         | UUID  | Source chunk ID                             |
| `similarity_score` | FLOAT | Similarity score between question and chunk |

---

## Document Processing Flow

| Step | Description                                                   |
| ---- | ------------------------------------------------------------- |
| 1    | User uploads a document.                                      |
| 2    | Backend validates file type, size, MIME type and readability. |
| 3    | File is stored with a safe generated name.                    |
| 4    | A record is created in `documents`.                           |
| 5    | Text is extracted from the file.                              |
| 6    | Text is split into chunks by the backend.                     |
| 7    | Embeddings are generated for each chunk.                      |
| 8    | Chunks and embeddings are saved in `document_chunks`.         |
| 9    | Document status is updated to `ready`.                        |

---

## Chat and Source Flow

| Step | Description                                                             |
| ---- | ----------------------------------------------------------------------- |
| 1    | User asks a question in a chat session.                                 |
| 2    | The question is saved in `chat_messages` with role `user`.              |
| 3    | The question is converted into an embedding.                            |
| 4    | pgvector searches similar chunks in `document_chunks`.                  |
| 5    | The most relevant chunks are sent to the LLM as context.                |
| 6    | The assistant answer is saved in `chat_messages` with role `assistant`. |
| 7    | Used chunks are linked to the answer in `message_sources`.              |

---

## Basic SQL Draft

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (
        file_type IN ('pdf', 'docx', 'txt', 'csv', 'xlsx')
    ),
    mime_type TEXT,
    file_size BIGINT,
    storage_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded' CHECK (
        status IN ('uploaded', 'processing', 'ready', 'failed')
    ),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    content TEXT NOT NULL,
    embedding VECTOR(1024),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (
        role IN ('user', 'assistant')
    ),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE message_sources (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    similarity_score FLOAT
);
```