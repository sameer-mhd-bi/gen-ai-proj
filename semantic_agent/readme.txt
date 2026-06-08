===============================================
SEMANTIC DATABASE AGENT - README
===============================================

PROJECT OVERVIEW
================
This project implements an intelligent database query agent that uses semantic search 
and vector embeddings to intelligently route queries to PostgreSQL and Neo4j. It combines 
LLM capabilities with graph-based metadata management for natural language database interaction.

ARCHITECTURE COMPONENTS
=======================

1. INGEST_SCHEMA.PY - Database Metadata Ingestion
---------------------------------------------------
Purpose: Extract database schema from PostgreSQL and populate Neo4j knowledge graph

Key Functions:
  - setup_database_schema_and_vector_index()
    * Creates unique constraints on Table and Column nodes
    * Builds native 384-dimension Vector Index in Neo4j for semantic search
    * Uses cosine similarity for embedding-based routing
    
  - scrape_and_ingest_metadata()
    * Queries PostgreSQL information_schema to extract:
      - Table names and column definitions
      - Data types (VARCHAR, INT, etc.)
      - Primary Key (PK) constraints
      - Foreign Key (FK) relationships and references
    * Generates 384-dimensional embeddings per table using SentenceTransformer
      (all-MiniLM-L6-v2 model)
    * Caches embeddings to avoid redundant model calls
    * Ingests into Neo4j with Cypher MERGE statements:
      - Creates :Table nodes with embedding vectors
      - Creates :Column nodes with metadata
      - Establishes :HAS_COLUMN relationships
      - Links :REFERENCES relationships for FK constraints

Data Flow:
  PostgreSQL Schema → Extract Metadata → Generate Embeddings → Neo4j Graph

2. AGENT.PY - Intelligent Query Routing Agent
----------------------------------------------
Purpose: AI-powered agent that understands natural language and routes queries to appropriate databases

Core Components:

  - Embedding Generation
    * Uses SentenceTransformer to convert user queries to 384-dim vectors
    * Enables semantic similarity search across schema metadata

  - Dynamic Schema Injection (System Prompt Hook)
    * Analyzes incoming user query for intent
    * If query is casual greeting (hi, hello, help, etc. <4 chars):
      - Returns friendly response without running database queries
    * Otherwise:
      - Performs vector search against Neo4j schema embeddings
      - Retrieves top 5 most semantically similar tables
      - Injects matched schema context into system prompt
    * Prevents hallucination by providing concrete schema reference

  - Semantic Query Routing (retrieve_relevant_schema)
    * Executes VECTOR INDEX search in Neo4j
    * Fetches matching tables, columns, data types, and relationships
    * Returns formatted schema context for LLM decision-making

  - Dual Query Execution Tools (with security guardrails)
    
    Tool 1: run_cypher_query(query)
      - Executes read-only Cypher queries against Neo4j
      - Use Case: Inspect schema metadata, relationships, graph structure
      - Blocked Commands: DELETE, REMOVE, SET, CREATE, MERGE, DROP
      - Returns: First 20 results
    
    Tool 2: run_postgres_query(sql_query)
      - Executes read-only SQL queries against PostgreSQL
      - Use Case: Fetch actual customer data, financial records
      - Blocked Commands: DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE
      - Returns: First 20 rows as dictionary format

  - Enterprise Monitoring
    * Integrated with Logfire for:
      - AI agent execution tracing
      - Pydantic model validation logs
      - Performance metrics and debugging

EXECUTION FLOW
==============
1. User submits natural language query via web interface
2. Agent receives query and triggers system_prompt decorator
3. Query embedding generated and semantically searched in Neo4j Vector Index
4. Matching schema context injected into LLM instructions
5. LLM (GPT-4o) decides which tool to call:
   - Schema questions → run_cypher_query
   - Data queries → run_postgres_query
6. Tool executes against appropriate database (read-only)
7. Results returned to user

SECURITY MODEL
==============
- All queries are READ-ONLY (SELECT/SEARCH only)
- Mutation operations (DELETE, UPDATE, CREATE, DROP) are explicitly blocked
- Query keywords checked before execution
- No credential exposure in tool responses
- Lowercase normalization prevents SQL injection via case manipulation

DEPLOYMENT
==========
Start the web server:
  uvicorn agent:app --host 127.0.0.1 --port 7932

Access the agent at: http://127.0.0.1:7932

DEPENDENCIES
============
- pydantic_ai: AI agent framework
- sentence_transformers: SentenceTransformer for embeddings
- neo4j: Neo4j graph database driver
- psycopg2: PostgreSQL connection adapter
- logfire: Enterprise monitoring and observability
- python-dotenv: Environment variable management

DATABASE REQUIREMENTS
=====================
- PostgreSQL instance with populated schema
- Neo4j 5.0+ with Vector Index support (Cypher 25 compatible)
- Both configured via .env file with credentials