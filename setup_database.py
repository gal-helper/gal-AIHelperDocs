# setup_database.py - Script to setup database with pgvector
import asyncio
import asyncpg
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import config

async def setup_database():
    """Setup database with pgvector support"""
    print("=" * 60)
    print("Setting up database with pgvector support")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        print("Connected to database")
        
        # 1. Create pgvector extension
        print("\n1. Creating pgvector extension...")
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("pgvector extension created or already exists")
        except Exception as e:
            print(f"Error creating pgvector extension: {e}")
            print("Make sure pgvector is installed on your PostgreSQL server")
            await conn.close()
            return False
        
        # 2. Drop existing tables if they exist
        print("\n2. Cleaning up existing tables...")
        await conn.execute("DROP TABLE IF EXISTS query_history CASCADE")
        await conn.execute("DROP TABLE IF EXISTS document_chunks CASCADE")
        await conn.execute("DROP TABLE IF EXISTS documents CASCADE")
        print("Existing tables dropped")
        
        # 3. Create documents table
        print("\n3. Creating documents table...")
        await conn.execute("""
            CREATE TABLE documents (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                file_path TEXT,
                file_type VARCHAR(50),
                file_size BIGINT,
                content TEXT,
                total_chunks INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("documents table created")
        
        # 4. Create document_chunks table with pgvector vector type
        print("\n4. Creating document_chunks table with vector support...")
        await conn.execute(f"""
            CREATE TABLE document_chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_vector vector({config.EMBEDDING_DIM}),
                token_count INTEGER,
                metadata JSONB DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("document_chunks table created with vector column")
        
        # 5. Create query_history table
        print("\n5. Creating query_history table...")
        await conn.execute("""
            CREATE TABLE query_history (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT,
                source_documents TEXT[],
                chunk_count INTEGER DEFAULT 0,
                response_time FLOAT,
                asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("query_history table created")
        
        # 6. Create indexes
        print("\n6. Creating indexes...")
        
        # Vector index for similarity search
        try:
            await conn.execute("""
                CREATE INDEX idx_chunks_vector 
                ON document_chunks USING ivfflat (content_vector vector_cosine_ops);
            """)
            print("Vector index created")
        except Exception as e:
            print(f"Warning: Could not create vector index: {e}")
        
        # Other indexes
        await conn.execute("CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);")
        print("document_id index created")
        
        await conn.execute("CREATE INDEX idx_query_asked_at ON query_history(asked_at DESC);")
        print("query_history index created")
        
        # 7. Verify tables
        print("\n7. Verifying table creation...")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"Created tables: {[t['table_name'] for t in tables]}")
        
        await conn.close()
        
        print("\n" + "=" * 60)
        print("Database setup completed successfully!")
        print("Tables are ready for vector search with pgvector")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

async def test_vector_search():
    """Test vector search functionality"""
    print("\n" + "=" * 60)
    print("Testing vector search functionality")
    print("=" * 60)
    
    try:
        from ai_service import ai_service
        
        # Test embedding generation
        test_text = "This is a test for vector search"
        embedding = await ai_service.get_embedding(test_text)
        print(f"Generated embedding with {len(embedding)} dimensions")
        
        # Test database connection and search
        from database import db_service
        
        if not await db_service.connect():
            print("Failed to connect to database")
            return False
        
        # Test vector search with empty database (should return empty)
        results = await db_service.search_similar_chunks(embedding, limit=3)
        print(f"Vector search returned {len(results)} results (expected: 0 for empty DB)")
        
        # Test keyword search
        keyword_results = await db_service.keyword_search("test", limit=3)
        print(f"Keyword search returned {len(keyword_results)} results")
        
        print("\nVector search test completed")
        return True
        
    except Exception as e:
        print(f"Vector search test failed: {e}")
        return False

async def main():
    """Main function"""
    print("Database Setup for pgvector Support")
    print("=" * 60)
    
    confirm = input("This will drop and recreate all tables. Continue? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("Operation cancelled.")
        return
    
    # Setup database
    if not await setup_database():
        print("Database setup failed.")
        return
    
    # Test vector search
    print("\n" + "=" * 60)
    print("Testing the setup...")
    print("=" * 60)
    
    await test_vector_search()
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("\nNext steps:")
    print("1. Run the RAG system: python cli_client.py --interactive")
    print("2. Upload a document: python cli_client.py --upload <file.txt>")
    print("3. Ask questions with vector search")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())