from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import spacy
from spacy.matcher import Matcher
from transformers import pipeline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import random
from openai import OpenAI
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv()

try:
    openai_client = OpenAI()
except Exception as e:
    print(f"Warning: OpenAI client initialization failed: {e}")
    openai_client = None

class WorkflowExtraction(BaseModel):
    claim_id: str = Field(description="The claim ID extracted or generated")
    policy: str = Field(description="The policy number")
    customer_name: str = Field(description="The customer's name")
    peril: str = Field(description="The peril (e.g. Windstorm)")
    damage_type: str = Field(description="The damage type")
    structure: str = Field(description="The structure damaged")
    estimated_loss: str = Field(description="The estimated loss as a string")
    highlighted_text: str = Field(description="The original text but with key entities wrapped in <b> tags")
    fraud_probability: str = Field(description="Fraud probability percentage, e.g. '4%'")
    coverage_confidence: str = Field(description="Coverage confidence percentage, e.g. '93%'")
    historical_matches: str = Field(description="Number of historical matches, e.g. '184'")
    semantic_similarity: str = Field(description="Semantic similarity percentage, e.g. '97%'")
    recommendation: str = Field(description="One of: 'Approve', 'Manual Review', 'Reject'")
    reasoning: str = Field(description="A short reasoning paragraph")

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

DEFAULT_CHUNK_SIZE = 600
DEFAULT_OVERLAP = 100
DEFAULT_N_RESULTS = 3

# Create folders if they don't exist
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
Path(DB_FOLDER).mkdir(parents=True, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize ChromaDB and SentenceTransformer
# client = chromadb.PersistentClient(path=DB_FOLDER)
client = None
try:
    print("Loading SentenceTransformer model ('all-MiniLM-L6-v2') for semantic search...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Warning: Failed to load SentenceTransformer: {e}")
    model = None

# Initialize spaCy NLP model for knowledge graph extraction
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    print("spaCy model 'en_core_web_sm' not found. Please run: python -m spacy download en_core_web_sm")
    nlp = None

# Initialize Zero-Shot Classification Pipeline
try:
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
except Exception as e:
    print(f"Error loading transformers pipeline: {e}")
    classifier = None

# Taxonomy Tree for Classification
import json
import os

TAXONOMY_FILE_PATH = os.path.join(os.path.dirname(__file__), 'taxonomy_tree.json')

def load_taxonomy_tree():
    if not os.path.exists(TAXONOMY_FILE_PATH):
        default_tree = {
            "Property Insurance": {
                "Commercial Property": {
                    "Building Property Coverage": {
                        "Windstorm Damage": ["Roof Structure Failure", "Broken Window Panes"],
                        "Water Damage": ["Internal Pipe Burst", "External Flood Ingress"]
                    },
                    "Business Personal Property": {
                        "Water Damage Contents": ["Inventory Stock Spoilage", "Machinery Short-Circuit"],
                        "Fire Damage": ["Smoke Discoloration", "Total Equipment Loss"]
                    }
                }
            },
            "Casualty Insurance": {
                "Auto Liability": {
                    "Bodily Injury Liability": {
                        "Third Party Rear-End": ["Cervical Whiplash", "Soft Tissue Strain"],
                        "Intersection Collision": ["Upper Extremity Fractures", "Concussion Trauma"]
                    }
                },
                "Workers Compensation": {
                    "Medical Only Benefits": {
                        "Occupational Slip and Fall": ["Ankle Fracture", "Wrist Sprain"],
                        "Repetitive Motion Strain": ["Carpal Tunnel Syndrome", "Tendonitis Flareup"]
                    },
                    "Indemnity / Lost Wages": {
                        "Industrial Machinery Accident": ["Amputation Rehabilitation", "Severe Laceration Recovery"]
                    }
                },
                "General Liability": {
                    "Bodily Injury Coverage": {
                        "Slip Trip or Fall Incident": ["Upper Extremity Fractures", "Soft Tissue Injury"]
                    }
                }
            }
        }
        with open(TAXONOMY_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_tree, f, indent=4)
        return default_tree
    
    with open(TAXONOMY_FILE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

taxonomy_tree = load_taxonomy_tree()
CONFIDENCE_THRESHOLD = 0.20


def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_chunks_from_pdf(pdf_path, chunk_size=DEFAULT_CHUNK_SIZE, overlap=DEFAULT_OVERLAP):
    """Extract and chunk PDF with overlap for better context, tracking chunk numbers"""
    try:
        reader = PdfReader(pdf_path)
        chunks_with_pages = []
        chunk_number = 1

        for page_num, page in enumerate(reader.pages, 1):
            content = page.extract_text()
            if content:
                # Split content into chunks with overlap
                for i in range(0, len(content), chunk_size - overlap):
                    chunk = content[i:i + chunk_size].strip()
                    if chunk:
                        chunks_with_pages.append({
                            'content': chunk,
                            'chunk_number': chunk_number
                        })
                        chunk_number += 1

        if not chunks_with_pages:
            return []

        return chunks_with_pages
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        return []

def extract_sentences(text):
    """
    Extract sentences from text using spaCy.
    
    1. Loads the English language model 'en_core_web_sm', which provides
       tokenization, part-of-speech tagging, and sentence boundary detection.
    2. Passes the extracted text to the NLP pipeline, creating a Doc
       object that stores linguistic annotations.
    3. Iterates through the detected sentence spans (doc.sents) and
       collects clean, non-empty sentence strings into a list called sentences.
    4. Returns the total number of sentences extracted.
    
    Args:
        text (str): The text to extract sentences from
    
    Returns:
        list: A list of sentences
    """
    if not nlp:
        return []
    
    try:
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        print(f"Extracted {len(sentences)} sentences from text")
        return sentences
    except Exception as e:
        print(f"Error extracting sentences: {e}")
        return []

def extract_subject_object(sentence):
    """
    Extract subject and object from a sentence using dependency parsing.
    
    1. Initialize empty strings for subject (subj) and object (obj).
    2. Track compound and modifier prefixes (e.g., "neural network").
    3. For each token:
       - Skip punctuation.
       - Combine consecutive compounds and modifiers.
       - When encountering a "subj" dependency, assemble and store the subject.
       - When encountering an "obj" dependency, assemble and store the object.
    4. Return both entities as a two-element list [subject, object].
    
    This method works well for simple declarative sentences and forms the
    foundation for building triplet-based extractions such as:
    (subject, relation, object)
    
    Args:
        sentence (str): A single sentence to analyze
    
    Returns:
        list: A list containing [subject, object] strings
    """
    if not nlp:
        return ["", ""]
    
    try:
        doc = nlp(sentence)
        subj = ""
        obj = ""
        
        for token in doc:
            # Skip punctuation
            if token.pos_ == "PUNCT":
                continue
            
            # Extract subject
            if token.dep_ == "nsubj" or token.dep_ == "nsubjpass":
                # Collect all related tokens (compounds, modifiers, the token itself)
                subj_tokens = [token]
                for child in token.head.children:
                    # Only add children that are compounds/modifiers and not the token itself
                    if child != token and child.dep_ in ["compound", "amod", "det"]:
                        subj_tokens.append(child)
                # Sort by position in sentence to maintain word order
                subj_tokens.sort(key=lambda t: t.i)
                subj = " ".join([t.text for t in subj_tokens])
            
            # Extract object
            if token.dep_ == "dobj" or token.dep_ == "attr":
                # Collect all related tokens (compounds, modifiers, the token itself)
                obj_tokens = [token]
                for child in token.head.children:
                    # Only add children that are compounds/modifiers and not the token itself
                    if child != token and child.dep_ in ["compound", "amod", "det"]:
                        obj_tokens.append(child)
                # Sort by position in sentence to maintain word order
                obj_tokens.sort(key=lambda t: t.i)
                obj = " ".join([t.text for t in obj_tokens])
        
        return [subj, obj]
    except Exception as e:
        print(f"Error extracting subject/object: {e}")
        return ["", ""]

def extract_relation(sentence):
    """
    Extract the relation/predicate from a sentence using pattern matching.
    
    1. The sentence is parsed into a spaCy Doc object.
    2. A Matcher is initialized on the model's vocabulary to identify
       dependency patterns corresponding to the main predicate.
    3. The pattern used captures:
       - The main verb (dependency label ROOT)
       - Optional prepositions (prep)
       - Optional agents (agent)
       - Optional adjectives (ADJ)
       This allows extraction of relations like:
       "is associated with", "was treated by", "causes", etc.
    4. The last matching span from the matcher is selected as the relation.
    5. If no match is found, an empty string is returned.
    
    Args:
        sentence (str): A single sentence to analyze
    
    Returns:
        str: The extracted relation/verb phrase
    """
    if not nlp:
        return ""
    
    try:
        doc = nlp(sentence)
        matcher = Matcher(nlp.vocab)
        
        # Pattern to match main verb (ROOT) and related tokens
        pattern = [
            {"dep": "ROOT", "pos": "VERB"},
            {"dep": {"IN": ["prep", "agent", "acomp"]}, "OP": "*"},
            {"pos": "ADJ", "OP": "*"}
        ]
        
        matcher.add("RELATION", [pattern])
        matches = matcher(doc)
        
        if matches:
            # Get the last match
            match_id, start, end = matches[-1]
            relation = doc[start:end].text
            return relation.strip()
        
        # Fallback: find the ROOT verb
        for token in doc:
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                return token.text
        
        return ""
    except Exception as e:
        print(f"Error extracting relation: {e}")
        return ""

@app.route('/api/search', methods=['POST'])
def search():
    """
    API endpoint to search in chromadb collections
    """
    data = request.get_json()
    query = data.get('query', '')
    collection_name = data.get('collection', 'default')
    n_results_param = data.get('n_results', DEFAULT_N_RESULTS) # Default if not provided
    
    try:
        n_results = int(n_results_param)
        if n_results <= 0:
            raise ValueError("n_results must be a positive integer.")
    except (ValueError, TypeError):
        return jsonify({'error': 'n_results must be a positive integer'}), 400
    
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
            query_embeddings=[query_vector], # type: ignore
            n_results=n_results,
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
                    'chunk_number': int(metadata['chunk_number']) if metadata.get('chunk_number') not in (None, '', 'None') else None,
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
    chunk_size_param = data.get('chunk_size', DEFAULT_CHUNK_SIZE) # Default if not provided
    overlap_param = data.get('overlap', DEFAULT_OVERLAP)         # Default if not provided
    
    if not pdf_filename or not collection_name:
        return jsonify({'error': 'Filename and collection_name are required'}), 400
    
    try:
        chunk_size = int(chunk_size_param)
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer.")
    except (ValueError, TypeError):
        return jsonify({'error': 'chunk_size must be a positive integer'}), 400

    try:
        overlap = int(overlap_param)
        if overlap < 0: # Overlap can be 0, but not negative
            raise ValueError("overlap must be a non-negative integer.")
        if overlap >= chunk_size:
            return jsonify({'error': 'overlap must be less than chunk_size'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'overlap must be a non-negative integer'}), 400

    try:
        # Build full path to PDF
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(pdf_filename))
        
        if not os.path.exists(pdf_path):
            return jsonify({'error': f'PDF file not found: {pdf_filename}'}), 404
        
        # Get chunks from PDF
        chunks_with_pages = get_chunks_from_pdf(pdf_path, chunk_size=chunk_size, overlap=overlap)
        if not chunks_with_pages:
            return jsonify({'error': 'No text could be extracted from PDF'}), 400
        
        # Create or get collection
        collection = client.get_or_create_collection(collection_name)
        
        # Generate embeddings and add to collection
        ids = [f"{pdf_filename}_{i}" for i in range(len(chunks_with_pages))]
        documents = [chunk['content'] for chunk in chunks_with_pages]
        embeddings = model.encode(documents).tolist()
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=[{
                "source": pdf_filename,
                "chunk_id": i,
                "chunk_number": int(chunk['chunk_number'])
            } for i, chunk in enumerate(chunks_with_pages)]
        )
        
        response = {
            'status': 'success',
            'message': f'Successfully vectorized and stored {len(chunks_with_pages)} chunks from {pdf_filename}',
            'collection': collection_name,
            'chunks_count': len(chunks_with_pages),
            'pdf_file': pdf_filename
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({'error': f'Vectorization failed: {str(e)}'}), 500

@app.route('/api/collections/<collection_name>/chunks', methods=['GET'])
def get_collection_chunks(collection_name):
    """
    API endpoint to fetch all chunks from a specific collection
    """
    try:
        safe_name = secure_filename(collection_name)
        collection = client.get_collection(safe_name)
        
        # Get all documents and metadata from the collection
        results = collection.get(include=['documents', 'metadatas'])
        
        chunks = []
        if results and results['documents']:
            for idx, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
                chunks.append({
                    'id': idx + 1,
                    'content': doc,
                    'source': metadata.get('source', 'unknown') if metadata else 'unknown',
                    'chunk_id': metadata.get('chunk_id', idx) if metadata else idx,
                    'chunk_number': metadata.get('chunk_number') if metadata else None
                })
        
        return jsonify({
            'status': 'success',
            'collection': collection_name,
            'chunks': chunks,
            'total_chunks': len(chunks)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to fetch chunks: {str(e)}'}), 500

@app.route('/api/search/dimensions', methods=['GET'])
def get_dimension_stats():
    """
    API endpoint to return per-dimension values of the query embedding vector.
    Accepts 'collection' and 'query' as query parameters.
    Returns a JSON array of { dimension_index, value } objects representing
    each dimension of the encoded query vector.
    """
    collection_name = request.args.get('collection', '')
    query = request.args.get('query', '')

    if not collection_name:
        return jsonify({'error': 'collection query parameter is required'}), 400

    if not query:
        return jsonify({'error': 'query parameter is required'}), 400

    try:
        # Encode the query text into a vector
        query_vector = model.encode(query).tolist()

        # Build the dimension array from the query vector
        dimension_data = [
            {'dimension_index': idx, 'value': value}
            for idx, value in enumerate(query_vector)
        ]

        return jsonify(dimension_data), 200

    except Exception as e:
        return jsonify({'error': f'Failed to compute dimension data: {str(e)}'}), 500

@app.route('/api/knowledge-graph', methods=['POST'])
def knowledge_graph():
    """
    API endpoint to extract knowledge graph (triplets) from a PDF using spaCy.
    
    Process:
    1. Extracts text from a PDF file
    2. Segments text into individual sentences using spaCy
    3. Extracts subject, predicate (relation), and object from each sentence
    4. Returns structured triplets for knowledge graph construction
    
    Request JSON:
    {
        "filename": "document.pdf"
    }
    
    Response:
    {
        "status": "success",
        "filename": "document.pdf",
        "total_sentences": 100,
        "triplets": [
            {
                "subject": "subject text",
                "predicate": "relation text",
                "object": "object text"
            },
            ...
        ]
    }
    """
    if not nlp:
        return jsonify({'error': 'spaCy model not initialized. Please download: python -m spacy download en_core_web_sm'}), 500
    
    data = request.get_json()
    pdf_filename = data.get('filename', '')
    
    if not pdf_filename:
        return jsonify({'error': 'Filename is required'}), 400
    
    try:
        # Build full path to PDF
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(pdf_filename))
        
        if not os.path.exists(pdf_path):
            return jsonify({'error': f'PDF file not found: {pdf_filename}'}), 404
        
        # Extract full text from PDF without chunking (avoid duplicates from overlapping chunks)
        try:
            reader = PdfReader(pdf_path)
            full_text = ""
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    full_text += content + "\n"
        except Exception as e:
            return jsonify({'error': f'Failed to extract text from PDF: {str(e)}'}), 400
        
        if not full_text.strip():
            return jsonify({'error': 'No text could be extracted from PDF'}), 400
        
        # Extract sentences
        sentences = extract_sentences(full_text)
        if not sentences:
            return jsonify({'error': 'No sentences could be extracted from text'}), 400
        
        # Extract triplets (subject, predicate, object) from each sentence
        # Use a set to track unique triplets and avoid duplicates
        seen_triplets = set()
        triplets = []
        
        for sentence in sentences:
            if len(sentence.strip()) > 5:  # Skip very short sentences
                # Extract subject and object
                subj_obj = extract_subject_object(sentence)
                subject = subj_obj[0].strip()
                obj = subj_obj[1].strip()
                
                # Extract relation/predicate
                predicate = extract_relation(sentence).strip()
                
                # Only add triplet if all three components are present and not a duplicate
                if subject and predicate and obj:
                    # Create a unique key for this triplet to avoid duplicates
                    triplet_key = (subject.lower(), predicate.lower(), obj.lower())
                    
                    if triplet_key not in seen_triplets:
                        seen_triplets.add(triplet_key)
                        triplets.append({
                            "subject": subject,
                            "predicate": predicate,
                            "object": obj
                        })
        
        response = {
            'status': 'success',
            'filename': pdf_filename,
            'total_sentences': len(sentences),
            'triplets_extracted': len(triplets),
            'triplets': triplets,
            'message': f'Successfully extracted {len(triplets)} unique triplets from {len(sentences)} sentences'
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({'error': f'Knowledge graph extraction failed: {str(e)}'}), 500

def plot_claim_hierarchy_base64(claim_num, text, path_labels, path_scores, final_score):
    plt.figure(figsize=(10, 5))
    x_positions = [0, 1, 2, 3, 4, 5]
    y_position = 0
    nodes = ["Insurance Root"] + path_labels
    scores_pct = [100.0] + [s * 100 for s in path_scores]

    for i in range(len(x_positions) - 1):
        plt.plot([x_positions[i], x_positions[i+1]], [y_position, y_position],
                 color='#bdc3c7', linestyle='-', linewidth=2, zorder=1)

    for i, (node_name, score) in enumerate(zip(nodes, scores_pct)):
        if i == 0:
            node_color = '#2c3e50'
        elif score >= 70.0:
            node_color = '#27ae60'
        elif score >= 40.0:
            node_color = '#f39c12'
        else:
            node_color = '#c0392b'

        plt.scatter(x_positions[i], y_position, color=node_color, s=400, zorder=2)
        label_text = f"{node_name}\n({score:.1f}%)" if i > 0 else node_name
        plt.text(x_positions[i], y_position + 0.15, label_text,
                 ha='center', va='bottom', fontsize=9, fontweight='bold',
                 bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3', edgecolor='#e2e8f0'))

    plt.title(f"Visual Taxonomy Path\nOverall Path Integrity: {final_score:.1f}%",
              fontsize=12, fontweight='bold', pad=20)
    plt.xlim(-0.5, 5.5)
    plt.ylim(-0.5, 0.8)
    plt.axis('off')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return img_base64


@app.route('/api/taxonomy-tree', methods=['GET'])
def get_taxonomy_tree():
    global taxonomy_tree
    return jsonify(taxonomy_tree), 200

@app.route('/api/taxonomy-tree', methods=['POST'])
def update_taxonomy_tree():
    global taxonomy_tree
    try:
        new_tree = request.get_json()
        if not new_tree or not isinstance(new_tree, dict):
            return jsonify({'error': 'Invalid taxonomy tree payload. Must be a JSON object.'}), 400
            
        with open(TAXONOMY_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_tree, f, indent=4)
            
        taxonomy_tree = new_tree
        return jsonify({'status': 'success', 'message': 'Taxonomy tree updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to update taxonomy tree: {str(e)}'}), 500

@app.route('/api/taxonomy-classify', methods=['POST'])
def taxonomy_classify():
    if not classifier:
        return jsonify({'error': 'Transformers classifier not loaded.'}), 500

    data = request.get_json()
    text = data.get('query', '')
    if not text:
        return jsonify({'error': 'Query text is required'}), 400

    try:
        plot_labels = []
        plot_scores = []
        joint_probability = 1.0
        path_nodes = []

        # Level 1
        l1_candidates = list(taxonomy_tree.keys())
        res_l1 = classifier(text, candidate_labels=l1_candidates)
        top_l1, score_l1 = res_l1['labels'][0], res_l1['scores'][0]
        joint_probability *= score_l1
        path_nodes.append(f"[L1 Line of Biz]: {top_l1} ({score_l1:.1%})")
        plot_labels.append(top_l1)
        plot_scores.append(score_l1)

        # Level 2
        l2_candidates = list(taxonomy_tree[top_l1].keys())
        res_l2 = classifier(text, candidate_labels=l2_candidates)
        top_l2, score_l2 = res_l2['labels'][0], res_l2['scores'][0]
        joint_probability *= score_l2
        path_nodes.append(f"[L2 Product]: {top_l2} ({score_l2:.1%})")
        plot_labels.append(top_l2)
        plot_scores.append(score_l2)

        # Level 3
        l3_candidates = list(taxonomy_tree[top_l1][top_l2].keys())
        res_l3 = classifier(text, candidate_labels=l3_candidates)
        top_l3, score_l3 = res_l3['labels'][0], res_l3['scores'][0]
        joint_probability *= score_l3
        path_nodes.append(f"[L3 Coverage]: {top_l3} ({score_l3:.1%})")
        plot_labels.append(top_l3)
        plot_scores.append(score_l3)

        # Level 4
        l4_candidates = list(taxonomy_tree[top_l1][top_l2][top_l3].keys())
        res_l4 = classifier(text, candidate_labels=l4_candidates)
        top_l4, score_l4 = res_l4['labels'][0], res_l4['scores'][0]

        if score_l4 < CONFIDENCE_THRESHOLD:
            alt_l3_candidates = [c for c in l3_candidates if c != top_l3]
            if alt_l3_candidates:
                top_l3 = alt_l3_candidates[0]
                l4_candidates = list(taxonomy_tree[top_l1][top_l2][top_l3].keys())
                res_l4 = classifier(text, candidate_labels=l4_candidates)
                top_l4, score_l4 = res_l4['labels'][0], res_l4['scores'][0]

                joint_probability = score_l1 * score_l2 * score_l3
                path_nodes[2] = f"[L3 Coverage (Backtracked)]: {top_l3} ({score_l3:.1%})"
                plot_labels[2] = f"{top_l3}\n(Backtracked)"

        joint_probability *= score_l4
        path_nodes.append(f"[L4 Peril]: {top_l4} ({score_l4:.1%})")
        plot_labels.append(top_l4)
        plot_scores.append(score_l4)

        # Level 5
        l5_candidates = taxonomy_tree[top_l1][top_l2][top_l3][top_l4]
        res_l5 = classifier(text, candidate_labels=l5_candidates)
        top_l5, score_l5 = res_l5['labels'][0], res_l5['scores'][0]
        joint_probability *= score_l5
        path_nodes.append(f"[L5 Cause]: 🛑 {top_l5} ({score_l5:.1%})")
        plot_labels.append(top_l5)
        plot_scores.append(score_l5)

        overall_percentage = joint_probability * 100
        
        img_base64 = plot_claim_hierarchy_base64(1, text, plot_labels, plot_scores, overall_percentage)

        return jsonify({
            'status': 'success',
            'path_nodes': path_nodes,
            'overall_score': overall_percentage,
            'image_base64': img_base64,
            'plot_labels': plot_labels,
            'plot_scores': plot_scores
        })
    except Exception as e:
        return jsonify({'error': f'Classification failed: {str(e)}'}), 500



"""
================================================================================
                        API ENDPOINTS DOCUMENTATION
================================================================================

1. HEALTH CHECK
   ┌─ Endpoint: GET /api/health
   ├─ Description: Health check endpoint to verify API is running
   ├─ Parameters: None
   └─ Response: { 'status': 'ok', 'message': 'Flask API is running' }

2. DOCUMENT UPLOAD & MANAGEMENT
   ┌─ Endpoint: POST /api/upload
   ├─ Description: Upload a PDF file to the server
   ├─ Parameters:
   │  └─ file (multipart form data): PDF file to upload
   └─ Response: { 'status': 'success', 'message': '...', 'filename': '...', 'path': '...' }

   ┌─ Endpoint: GET /api/documents
   ├─ Description: List all uploaded PDF files
   ├─ Parameters: None
   └─ Response: { 'status': 'success', 'files': [...], 'count': 0 }

   ┌─ Endpoint: GET /api/documents/<filename>
   ├─ Description: Serve/display a specific PDF file
   ├─ Parameters: 
   │  └─ filename (path parameter): Name of the PDF file
   └─ Response: PDF file (application/pdf)

   ┌─ Endpoint: DELETE /api/documents/<filename>
   ├─ Description: Delete a specific PDF file
   ├─ Parameters:
   │  └─ filename (path parameter): Name of the PDF file to delete
   └─ Response: { 'status': 'success', 'message': '...' }

   ┌─ Endpoint: GET /api/pdf-list
   ├─ Description: List all available PDF files for dropdown selection
   ├─ Parameters: None
   └─ Response: { 'status': 'success', 'files': [...], 'count': 0 }

3. VECTORIZATION & COLLECTION MANAGEMENT
   ┌─ Endpoint: POST /api/vectorize
   ├─ Description: Vectorize PDF and store chunks in a ChromaDB collection
   ├─ Parameters (JSON):
   │  ├─ filename: Name of the PDF file to vectorize
   │  └─ collection_name: Name of the collection to store vectors
   ├─ Process:
   │  ├─ Extract text from PDF
   │  ├─ Split into chunks (chunk_size=600, overlap=100)
   │  ├─ Generate embeddings using SentenceTransformer
   │  └─ Store in ChromaDB collection
   └─ Response: { 'status': 'success', 'collection': '...', 'chunks_count': 0, 'pdf_file': '...' }

   ┌─ Endpoint: GET /api/collections
   ├─ Description: List all available collections with metadata
   ├─ Parameters: None
   └─ Response: { 'status': 'success', 'collections': [...], 'count': 0 }
   │  Each collection contains: { 'name': '...', 'count': 0, 'pdfs': [...] }

   ┌─ Endpoint: DELETE /api/collections/<collection_name>
   ├─ Description: Delete an entire collection and all its vectors
   ├─ Parameters:
   │  └─ collection_name (path parameter): Name of the collection to delete
   └─ Response: { 'status': 'success', 'message': '...' }

   ┌─ Endpoint: GET /api/collections/<collection_name>/chunks
   ├─ Description: Fetch all chunks from a specific collection
   ├─ Parameters:
   │  └─ collection_name (path parameter): Name of the collection
   └─ Response: { 'status': 'success', 'collection': '...', 'chunks': [...], 'total_chunks': 0 }
   │  Each chunk contains: { 'id': 0, 'content': '...', 'source': '...', 'chunk_id': 0 }
   │  Each chunk also contains: { 'chunk_number': 0 }

4. SEARCH
   ┌─ Endpoint: POST /api/search
   ├─ Description: Search for relevant documents in a collection
   ├─ Parameters (JSON):
   │  ├─ query: Search query string
   │  └─ collection: Name of the collection to search in
   ├─ Process:
   │  ├─ Encode query using SentenceTransformer
   │  ├─ Query ChromaDB collection for similar documents
   │  ├─ Return top 3 most relevant results
   │  └─ Calculate similarity scores
   └─ Response: { 'status': 'success', 'query': '...', 'collection': '...', 'results': [...], 'message': '...' }
   │  Each result contains: { 'content': '...', 'source': '...', 'chunk_number': 0, 'similarity': 0.0 }

5. KNOWLEDGE GRAPH EXTRACTION
   ┌─ Endpoint: POST /api/knowledge-graph
   ├─ Description: Extract knowledge graph triplets from a PDF using spaCy NLP
   ├─ Parameters (JSON):
   │  └─ filename: Name of the PDF file to process
   ├─ Process:
   │  ├─ Extract text from PDF
   │  ├─ Segment text into sentences using spaCy
   │  ├─ Extract subject, predicate, and object from each sentence
   │  ├─ Return structured triplets for knowledge graph construction
   │  └─ Filter out incomplete triplets
   ├─ Triplet Format: { "subject": "...", "predicate": "...", "object": "..." }
   └─ Response: { 'status': 'success', 'filename': '...', 'total_sentences': 0, 'triplets_extracted': 0, 'triplets': [...] }

================================================================================
                           HELPER FUNCTIONS
================================================================================

allowed_file(filename)
  └─ Description: Check if a file has an allowed extension (PDF only)
  └─ Returns: Boolean

get_chunks_from_pdf(pdf_path, chunk_size=600, overlap=100)
  ├─ Description: Extract text from PDF and split into overlapping chunks
  ├─ Parameters:
  │  ├─ pdf_path: Path to the PDF file
  │  ├─ chunk_size: Size of each chunk (default: 600 characters)
  │  └─ overlap: Overlap between chunks (default: 100 characters)
  └─ Returns: List of text chunks

extract_sentences(text)
  ├─ Description: Extract individual sentences from text using spaCy NLP
  ├─ Features:
  │  ├─ Loads English language model 'en_core_web_sm'
  │  ├─ Provides tokenization, POS tagging, and sentence boundary detection
  │  └─ Returns clean, non-empty sentence strings
  └─ Returns: List of sentences

extract_subject_object(sentence)
  ├─ Description: Extract subject and object entities from a sentence using dependency parsing
  ├─ Process:
  │  ├─ Uses dependency labels (nsubj, dobj, attr)
  │  ├─ Combines compound and modifier tokens
  │  └─ Handles both active and passive voice
  └─ Returns: List containing [subject, object]

extract_relation(sentence)
  ├─ Description: Extract the main relation/predicate from a sentence
  ├─ Features:
  │  ├─ Identifies ROOT verb (main predicate)
  │  ├─ Handles optional prepositions, agents, and adjectives
  │  ├─ Supports complex relations like "is associated with", "was treated by"
  │  └─ Uses pattern matching on dependency trees
  └─ Returns: Relation/verb phrase as string

================================================================================
                         DATABASE & CONFIGURATION
================================================================================

Upload Folder: backend/src_doc_files/
  └─ Stores uploaded PDF files

Database Folder: backend/knowledge_db/
  └─ ChromaDB persistent storage for vector embeddings

Max File Size: 50 MB

Embedding Model: sentence-transformers/all-MiniLM-L6-v2
  └─ Fast and efficient model for semantic search

================================================================================
"""

@app.route('/api/workflow/analyze', methods=['POST'])
def analyze_workflow():
    data = request.get_json()
    claim_text = data.get('text', '')
    
    if not claim_text:
        return jsonify({'error': 'Claim text is required'}), 400
        
    try:
        if not openai_client:
            return jsonify({'error': 'OpenAI client not configured. Please set OPENAI_API_KEY environment variable.'}), 500
            
        # 1. Extract and analyze via OpenAI
        completion = openai_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are an insurance claim analyzer AI. Extract the requested fields from the claim description and evaluate risk and coverage.\n"
                        "For factual metadata fields (customer_name, policy), if they are not explicitly mentioned in the description, set them to 'Unknown' (do not invent names or policy numbers).\n"
                        "For peril, damage_type, structure, and estimated_loss, infer them from the claim details if possible, otherwise set them to 'Unknown'.\n"
                        "For analytical fields (fraud_probability, coverage_confidence, recommendation, reasoning), perform a risk and coverage evaluation based on the claim text (do not set them to 'Unknown').\n"
                        "Highlight key entities in the text with <b> tags ONLY in the highlighted_text field. Do NOT include <b> or </b> tags in any other extracted fields."
                    )
                },
                {"role": "user", "content": f"Claim description:\n{claim_text}"}
            ],
            response_format=WorkflowExtraction,
        )
        
        extracted_data = json.loads(completion.choices[0].message.content)
        
        # Clean HTML helper to prevent <b> tags leakage in extracted fields
        def clean_html(val):
            if isinstance(val, str):
                return val.replace("<b>", "").replace("</b>", "").replace("<strong>", "").replace("</strong>", "")
            return val

        extracted_policy = clean_html(extracted_data.get("policy", "Unknown"))
        extracted_claim_id = clean_html(extracted_data.get("claim_id", "Unknown"))
        extracted_customer = clean_html(extracted_data.get("customer_name", "Unknown"))

        # Fetch all policies for this customer to display in the knowledge graph
        customer_policies = []
        if extracted_customer != "Unknown":
            try:
                import psycopg2
                conn = psycopg2.connect(dbname="insurance_db", user="postgres", password="root", host="localhost", port="5432")
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.policy_number, p.policy_type
                    FROM policies p
                    JOIN customers c ON p.customer_id = c.id
                    WHERE LOWER(TRIM(c.full_name)) = LOWER(TRIM(%s));
                """, (extracted_customer,))
                rows = cursor.fetchall()
                for row in rows:
                    customer_policies.append({
                        "policy_number": row[0],
                        "policy_type": row[1]
                    })
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Error fetching customer policies: {e}")

        # Database Validation for Policy if user provided it
        if extracted_policy != "Unknown":
            try:
                import psycopg2
                conn = psycopg2.connect(dbname="insurance_db", user="postgres", password="root", host="localhost", port="5432")
                cursor = conn.cursor()
                
                cursor.execute("SELECT 1 FROM policies WHERE TRIM(policy_number) = %s;", (extracted_policy.strip(),))
                if not cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return jsonify({'error': f"Policy '{extracted_policy}' was not found in the database."}), 400
                        
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Database validation exception: {e}")

        # 2. Taxonomy Classification
        def flatten_tree(tree, current_path=""):
            labels = []
            for k, v in tree.items():
                path = f"{current_path} > {k}" if current_path else k
                labels.append(path)
                if isinstance(v, dict):
                    labels.extend(flatten_tree(v, path))
                elif isinstance(v, list):
                    for item in v:
                        labels.append(f"{path} > {item}")
            return labels
            
        candidate_labels = flatten_tree(taxonomy_tree)
        taxonomy_path = "Insurance"
        
        if classifier:
            classification = classifier(claim_text, candidate_labels, multi_label=True)
            if classification['scores'][0] >= 0.05:
                best_match = classification['labels'][0]
                score_percentage = round(classification['scores'][0] * 100, 1)
                parts = best_match.split(" > ")
                taxonomy_html = "Insurance<br/>"
                indent = ""
                for part in parts:
                    taxonomy_html += f"{indent}└── {part}<br/>"
                    indent += "&nbsp;&nbsp;&nbsp;&nbsp;"
                taxonomy_html += f"<span style='color: #64748b; font-weight: 600;'>(Confidence: {score_percentage}%)</span>"
                taxonomy_path = taxonomy_html
        
        # 3. Vector Similarity Search for Similar Claims
        similar_claims = []
        if model:
            try:
                import psycopg2
                query_embedding = model.encode(claim_text).tolist()
                conn = psycopg2.connect(dbname="insurance_db", user="postgres", password="root", host="localhost", port="5432")
                cursor = conn.cursor()
                
                # Cosine similarity calculated directly in PostgreSQL using unnest and SQL array dot product
                cursor.execute("""
                    SELECT c.claim_id, c.description, c.peril, c.damage_type, c.estimated_loss, c.status, c.recommendation,
                        (
                            SELECT sum(a * b)
                            FROM unnest(c.embedding::double precision[]) WITH ORDINALITY AS x(a, i)
                            JOIN unnest(%s::double precision[]) WITH ORDINALITY AS y(b, j) ON x.i = y.j
                        ) / (
                            SQRT((SELECT sum(a * a) FROM unnest(c.embedding::double precision[]) AS a)) * 
                            SQRT((SELECT sum(b * b) FROM unnest(%s::double precision[]) AS b))
                        ) AS similarity
                    FROM claims c
                    ORDER BY similarity DESC
                    LIMIT 3;
                """, (query_embedding, query_embedding))
                
                rows = cursor.fetchall()
                for row in rows:
                    similar_claims.append({
                        "claim_id": row[0],
                        "description": row[1],
                        "peril": row[2],
                        "damage_type": row[3],
                        "estimated_loss": float(row[4]) if row[4] is not None else 0.0,
                        "status": row[5],
                        "recommendation": row[6],
                        "similarity": round(float(row[7]) * 100, 1) if row[7] is not None else 0.0
                    })
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Error searching similar claims in Postgres: {e}")

        # HTML fields are already cleaned using pre-defined clean_html

        # Assemble response
        response = {
            "status": "success",
            "extraction": {
                "claim_id": clean_html(extracted_data.get("claim_id", f"CLM-{random.randint(10000, 99999)}")),
                "policy": clean_html(extracted_data.get("policy", "Unknown")),
                "customer": clean_html(extracted_data.get("customer_name", "Unknown")),
                "source": "Web Portal",
                "highlighted_text": extracted_data.get("highlighted_text", claim_text),
                "peril": clean_html(extracted_data.get("peril", "Unknown")),
                "damage_type": clean_html(extracted_data.get("damage_type", "Unknown")),
                "structure": clean_html(extracted_data.get("structure", "Unknown")),
                "estimated_loss": clean_html(extracted_data.get("estimated_loss", "Unknown")),
            },
            "taxonomy_path": taxonomy_path,
            "knowledge_graph": {
                "nodes": [
                    clean_html(extracted_data.get("customer_name", "Customer")), 
                    clean_html(extracted_data.get("policy", "Policy")), 
                    "Coverage B", 
                    clean_html(extracted_data.get("structure", "Structure")), 
                    clean_html(extracted_data.get("peril", "Peril"))
                ],
                "reasoning": clean_html(extracted_data.get("reasoning", "Coverage evaluated."))
            },
            "risk_analytics": {
                "fraud_probability": clean_html(extracted_data.get("fraud_probability", "5%")),
                "coverage_confidence": clean_html(extracted_data.get("coverage_confidence", "90%")),
                "historical_matches": str(len(similar_claims)) if similar_claims else extracted_data.get("historical_matches", "0"),
                "semantic_similarity": f"{int(similar_claims[0]['similarity'])}%" if similar_claims else extracted_data.get("semantic_similarity", "80%")
            },
            "recommendation": clean_html(extracted_data.get("recommendation", "Manual Review")),
            "similar_claims": [{**c, "description": clean_html(c["description"]), "peril": clean_html(c["peril"]), "damage_type": clean_html(c["damage_type"]), "recommendation": clean_html(c["recommendation"])} for c in similar_claims],
            "customer_policies": customer_policies
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error in workflow analysis: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
