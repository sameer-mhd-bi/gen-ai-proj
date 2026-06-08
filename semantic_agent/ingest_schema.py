# ingest_schema.py
import os
import psycopg2
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path
from sentence_transformers import SentenceTransformer

load_dotenv(dotenv_path=Path('.') / '.env')

# 1. Initialize DB Drivers & Local MiniLM
embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
neo4j_driver = GraphDatabase.driver(
    "bolt://localhost:7687", auth=("neo4j", os.getenv("NEO4J_PASSWORD", "password123"))
)

def get_pg_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "bank_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "root"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

def setup_database_schema_and_vector_index():
    """Builds native Vector Indexes in Neo4j (Cypher 25 compatible)."""
    with neo4j_driver.session() as session:
        # Create standard constraints to enforce unique metadata keys
        session.run("CREATE CONSTRAINT table_unique_name IF NOT EXISTS FOR (t:Table) REQUIRE t.name IS UNIQUE")
        session.run("CREATE CONSTRAINT column_unique_id IF NOT EXISTS FOR (c:Column) REQUIRE c.id IS UNIQUE")
        
        # Create the 384-dimension Vector Index for semantic routing
        session.run("""
        CREATE VECTOR INDEX schema_embeddings IF NOT EXISTS
        FOR (n:Table) ON (n.embedding)
        OPTIONS {indexConfig: {
          `vector.dimensions`: 384,
          `vector.similarity_function`: 'cosine'
        }}
        """)
    print("✓ Neo4j Constraints and Vector Index verified.")

def scrape_and_ingest_metadata():
    """Extracts schemas from Postgres, generates local embeddings, and pipes to Neo4j."""
    setup_database_schema_and_vector_index()
    
    # Extract structural constraints from the relational views
    sql_query = """
    SELECT c.table_name, c.column_name, c.data_type,
           CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 'PK'
                WHEN tc.constraint_type = 'FOREIGN KEY' THEN 'FK' ELSE 'NONE' END as key_type,
           ccu.table_name AS referenced_table, ccu.column_name AS referenced_column
    FROM information_schema.columns c
    LEFT JOIN information_schema.key_column_usage kcu ON c.table_schema = kcu.table_schema 
        AND c.table_name = kcu.table_name AND c.column_name = kcu.column_name
    LEFT JOIN information_schema.table_constraints tc ON kcu.table_schema = tc.table_schema 
        AND kcu.table_name = tc.table_name AND kcu.constraint_name = tc.constraint_name
    LEFT JOIN information_schema.constraint_column_usage ccu ON tc.constraint_type = 'FOREIGN KEY' 
        AND tc.constraint_name = ccu.constraint_name
    WHERE c.table_schema = 'public'
    ORDER BY c.table_name, c.ordinal_position;
    """
    
    print("Scraping metadata fields from PostgreSQL...")
    pg_conn = get_pg_connection()
    with pg_conn.cursor() as cursor:
        cursor.execute(sql_query)
        metadata_rows = cursor.fetchall()
    pg_conn.close()

    # Pack metrics into standard batch maps
    batch_data = []
    # Keep track of generated embeddings per table to avoid redundant model calls
    table_embeddings = {}

    print("Generating local 384-dim embeddings...")
    for r in metadata_rows:
        table_name = r[0].lower() # Standardise everything to lowercase to avoid naming collisions
        column_name = r[1].lower()
        data_type = r[2]
        key_type = r[3]
        referenced_table = r[4].lower() if r[4] else None
        referenced_column = r[5].lower() if r[5] else None

        # Cache vector embedding values per table node context string
        if table_name not in table_embeddings:
            context_description = f"Database Table mapping: {table_name}. Contains data entries and system structural metadata."
            embedding_arr = embedding_model.encode(context_description)
            table_embeddings[table_name] = embedding_arr.tolist()

        batch_data.append({
            "table_name": table_name,
            "column_name": column_name,
            "data_type": data_type,
            "key_type": key_type,
            "referenced_table": referenced_table,
            "referenced_column": referenced_column,
            "embedding": table_embeddings[table_name]
        })

    # Execute graph compilation statement block
        # Corrected Cypher syntax inside ingest_schema.py
    cypher_ingestion = """
    UNWIND $rows AS row
    MERGE (t:Table {name: row.table_name})
    SET t.embedding = row.embedding
    
    MERGE (c:Column {id: row.table_name + '.' + row.column_name})
    SET c.name = row.column_name, c.dataType = row.data_type
    
    MERGE (t)-[:HAS_COLUMN]->(c)
    
    // FIXED: [1] added after THEN to give FOREACH a valid array to loop over
    FOREACH (_ IN CASE WHEN row.key_type = 'PK' THEN [1] ELSE [] END | SET c.isPrimaryKey = true)
    
    // FIXED: [1] added after THEN here as well
    FOREACH (_ IN CASE WHEN row.key_type = 'FK' AND row.referenced_table IS NOT NULL THEN [1] ELSE [] END |
        MERGE (targetTable:Table {name: row.referenced_table})
        MERGE (t)-[r:REFERENCES]->(targetTable)
        SET r.from_column = row.column_name, r.to_column = row.referenced_column
    )
    """

    
    print("Writing structural metadata payload into Neo4j graph...")
    with neo4j_driver.session() as session:
        session.run(cypher_ingestion, rows=batch_data)
        
    neo4j_driver.close()
    print("✓ Migration Complete! Your Knowledge Graph is populated and fully indexed.")

if __name__ == "__main__":
    scrape_and_ingest_metadata()
