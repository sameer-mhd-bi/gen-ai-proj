# Flask Backend Setup

## Prerequisites
- Python 3.7+
- pip

## Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Flask API

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### POST /api/search
Searches in chromadb collections for relevant documents based on a query.

**Request:**
```json
{
  "query": "delayed shipments",
  "collection": "supply_chain"
}
```

**Response:**
```json
{
  "query": "delayed shipments",
  "status": "success",
  "collection": "supply_chain",
  "results": [
    {
      "content": "Document chunk content...",
      "source": "document.pdf",
      "similarity": 0.85
    }
  ],
  "message": "Found 3 relevant documents"
}
```

### POST /api/upload
Uploads a PDF file to the `src_doc_files` folder.

**Request:**
- Form data with `file` field containing the PDF

**Response:**
```json
{
  "status": "success",
  "message": "File document.pdf uploaded successfully",
  "filename": "document.pdf",
  "path": "/path/to/src_doc_files/document.pdf"
}
```

### GET /api/documents
Retrieves a list of all uploaded PDF files.

**Response:**
```json
{
  "status": "success",
  "files": [
    {
      "name": "document.pdf",
      "size": 102400,
      "path": "/path/to/src_doc_files/document.pdf"
    }
  ],
  "count": 1
}
```

### GET /api/pdf-list
Retrieves list of available PDFs for dropdown selection.

**Response:**
```json
{
  "status": "success",
  "files": [
    {
      "name": "document.pdf",
      "size": 102400,
      "path": "/path/to/src_doc_files/document.pdf"
    }
  ],
  "count": 1
}
```

### POST /api/vectorize
Vectorizes a PDF and stores it in a chromadb collection.

**Request:**
```json
{
  "filename": "document.pdf",
  "collection_name": "supply_chain"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Successfully vectorized and stored 45 chunks from document.pdf",
  "collection": "supply_chain",
  "chunks_count": 45,
  "pdf_file": "document.pdf"
}
```

### GET /api/collections
Retrieves a list of all available chromadb collections.

**Response:**
```json
{
  "status": "success",
  "collections": [
    {
      "name": "supply_chain",
      "count": 45
    }
  ],
  "count": 1
}
```

### GET /api/health
Health check endpoint to verify the API is running.

**Response:**
```json
{
  "status": "ok",
  "message": "Flask API is running"
}
```

## File Storage & Database

- **Uploaded PDFs**: Stored in `backend/src_doc_files/` folder
- **ChromaDB Collections**: Stored in `backend/knowledge_db/` folder (automatically created)
- **Vector Embeddings**: Generated using SentenceTransformer model 'all-MiniLM-L6-v2'

## Workflow

1. **Upload PDF** (Documents Tab)
   - Upload a PDF file using the Documents tab

2. **Vectorize PDF** (Collections Tab)
   - Select the uploaded PDF from the dropdown
   - Enter a collection name
   - Click "Vectorize & Store"
   - The PDF will be extracted, chunked, and stored in ChromaDB

3. **Search** (Search Tab)
   - Enter a search query
   - The query is converted to embeddings and searched across the selected collection
   - Relevant chunks are retrieved and displayed with similarity scores
