from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

app = Flask(__name__)
# Enable CORS with specific configuration
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'src_doc_files')
DB_FOLDER = os.path.join(os.path.dirname(__file__), 'knowledge_db')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Create folders if they don't exist
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
Path(DB_FOLDER).mkdir(parents=True, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize ChromaDB and SentenceTransformer
client = chromadb.PersistentClient(path=DB_FOLDER)
model = SentenceTransformer('all-MiniLM-L6-v2')

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_chunks_from_pdf(pdf_path, chunk_size=600, overlap=100):
    """Extract and chunk PDF with overlap for better context"""
    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                full_text += content + "\n"

        if not full_text.strip():
            return []

        # Split into chunks with overlap
        chunks = []
        for i in range(0, len(full_text), chunk_size - overlap):
            chunk = full_text[i:i + chunk_size].strip()
            if chunk:
                chunks.append(chunk)

        return chunks
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        return []

@app.route('/api/search', methods=['POST'])
def search():
    """
    API endpoint to search in chromadb collections
    """
    data = request.get_json()
    query = data.get('query', '')
    collection_name = data.get('collection', 'default')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        # Try to get the collection
        try:
            collection = client.get_collection(collection_name)
        except:
            # If collection doesn't exist, return the query as-is
            return jsonify({
                'query': query,
                'status': 'success',
                'message': f'Search query: {query}',
                'results': []
            }), 200
        
        # Search in the collection
        query_vector = model.encode(query).tolist()
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=3,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for doc, metadata, distance in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                formatted_results.append({
                    'content': doc,
                    'source': metadata.get('source', 'unknown'),
                    'similarity': round(1 - distance, 3)
                })
        
        response = {
            'query': query,
            'status': 'success',
            'collection': collection_name,
            'results': formatted_results,
            'message': f'Found {len(formatted_results)} relevant documents'
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """
    Health check endpoint
    """
    return jsonify({'status': 'ok', 'message': 'Flask API is running'}), 200

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    API endpoint to upload PDF files
    """
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if file is PDF
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Save the file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        response = {
            'status': 'success',
            'message': f'File {filename} uploaded successfully',
            'filename': filename,
            'path': filepath
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/documents', methods=['GET'])
def get_documents():
    """
    API endpoint to list all uploaded PDF files
    """
    try:
        files = []
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if filename.lower().endswith('.pdf'):
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file_size = os.path.getsize(filepath)
                    files.append({
                        'name': filename,
                        'size': file_size,
                        'path': filepath
                    })
        
        return jsonify({
            'status': 'success',
            'files': files,
            'count': len(files)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to fetch documents: {str(e)}'}), 500

@app.route('/api/documents/<filename>', methods=['GET', 'DELETE'])
def serve_pdf(filename):
    """
    API endpoint to serve PDF files for viewing or delete them
    """
    try:
        # Secure the filename to prevent directory traversal
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({'error': f'PDF file not found: {filename}'}), 404
        
        # Check if file is a PDF
        if not safe_filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files can be served'}), 400
        
        # Handle GET request - serve the file
        if request.method == 'GET':
            return send_file(
                filepath,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=safe_filename
            )
        
        # Handle DELETE request - delete the file
        elif request.method == 'DELETE':
            try:
                os.remove(filepath)
                return jsonify({
                    'status': 'success',
                    'message': f'Successfully deleted {filename}'
                }), 200
            except Exception as e:
                return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Failed to serve PDF: {str(e)}'}), 500

@app.route('/api/pdf-list', methods=['GET'])
def get_pdf_list():
    """
    API endpoint to list all available PDF files for dropdown
    """
    try:
        files = []
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if filename.lower().endswith('.pdf'):
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file_size = os.path.getsize(filepath)
                    files.append({
                        'name': filename,
                        'size': file_size,
                        'path': filepath
                    })
        
        return jsonify({
            'status': 'success',
            'files': files,
            'count': len(files)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to fetch PDF list: {str(e)}'}), 500

@app.route('/api/collections', methods=['GET'])
def get_collections():
    """
    API endpoint to list all available collections with PDF sources
    """
    try:
        collections = client.list_collections()
        collection_list = []
        for collection in collections:
            # Get all documents in the collection to extract unique PDF sources
            results = collection.get()
            pdf_sources = set()
            
            if results and results['metadatas']:
                for metadata in results['metadatas']:
                    if metadata and 'source' in metadata:
                        pdf_sources.add(metadata['source'])
            
            collection_list.append({
                'name': collection.name,
                'count': collection.count(),
                'pdfs': sorted(list(pdf_sources))
            })
        
        return jsonify({
            'status': 'success',
            'collections': collection_list,
            'count': len(collection_list)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to fetch collections: {str(e)}'}), 500

@app.route('/api/collections/<collection_name>', methods=['DELETE'])
def delete_collection(collection_name):
    """
    API endpoint to delete a collection
    """
    try:
        safe_name = secure_filename(collection_name)
        
        # Delete the collection
        client.delete_collection(name=safe_name)
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully deleted collection "{collection_name}"'
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to delete collection: {str(e)}'}), 500

@app.route('/api/vectorize', methods=['POST'])
def vectorize_pdf():
    """
    API endpoint to vectorize and store a PDF in a collection
    """
    data = request.get_json()
    pdf_filename = data.get('filename', '')
    collection_name = data.get('collection_name', '')
    
    if not pdf_filename or not collection_name:
        return jsonify({'error': 'Filename and collection_name are required'}), 400
    
    try:
        # Build full path to PDF
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(pdf_filename))
        
        if not os.path.exists(pdf_path):
            return jsonify({'error': f'PDF file not found: {pdf_filename}'}), 404
        
        # Get chunks from PDF
        chunks = get_chunks_from_pdf(pdf_path)
        if not chunks:
            return jsonify({'error': 'No text could be extracted from PDF'}), 400
        
        # Create or get collection
        collection = client.get_or_create_collection(collection_name)
        
        # Generate embeddings and add to collection
        ids = [f"{pdf_filename}_{i}" for i in range(len(chunks))]
        embeddings = model.encode(chunks).tolist()
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"source": pdf_filename, "chunk_id": i} for i in range(len(chunks))]
        )
        
        response = {
            'status': 'success',
            'message': f'Successfully vectorized and stored {len(chunks)} chunks from {pdf_filename}',
            'collection': collection_name,
            'chunks_count': len(chunks),
            'pdf_file': pdf_filename
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({'error': f'Vectorization failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
