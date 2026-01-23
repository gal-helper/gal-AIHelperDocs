# setup.py - Installation and setup script
import os
import sys
import subprocess
import argparse

def check_dependencies():
    """Check and install Python dependencies"""
    print("Checking Python dependencies...")
    
    requirements = [
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "asyncpg>=0.29.0",
        "aiohttp>=3.9.0",
        "numpy>=1.24.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0"
    ]
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + requirements)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def create_env_file():
    """Create .env file with configuration"""
    env_content = """# AI RAG System Configuration

# DeepSeek API
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# Database Configuration (RDS PostgreSQL)
DB_HOST=pgm-uf6n7qif31xum72r.pg.rds.aliyuncs.com
DB_PORT=5432
DB_NAME=gal_helper
DB_USER=dick2416910961
DB_PASSWORD=11a22B33(

# Optional: Customize these if needed
# EMBEDDING_DIM=1536
# CHUNK_SIZE=1000
# CHUNK_OVERLAP=200
# SIMILARITY_THRESHOLD=0.7
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Created .env file")
    print("Please edit .env to add your DeepSeek API key")

def create_example_documents():
    """Create example documents directory"""
    os.makedirs("documents", exist_ok=True)
    
    # Create example knowledge base files
    examples = {
        "machine_learning.txt": """Machine Learning Basics

Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed.

Types of Machine Learning:
1. Supervised Learning: Learning from labeled data
2. Unsupervised Learning: Finding patterns in unlabeled data
3. Reinforcement Learning: Learning through rewards and penalties

Common Algorithms:
- Linear Regression
- Decision Trees
- Neural Networks
- Support Vector Machines

Applications:
- Image recognition
- Natural language processing
- Recommendation systems
- Fraud detection""",
        
        "deepseek_api.txt": """DeepSeek API Documentation

DeepSeek provides free AI API services for developers.

Available Endpoints:
1. Chat Completion: /v1/chat/completions
   Model: deepseek-chat
   
2. Embeddings: /v1/embeddings
   Model: deepseek-embedding
   
3. Models List: /v1/models

API Key: Obtain from https://platform.deepseek.com/

Rate Limits: Free tier has generous limits

Embedding Dimensions: 1536 dimensions

Response Format: Compatible with OpenAI API format""",
        
        "system_guide.txt": """AI RAG System User Guide

This system allows you to:
1. Upload documents in TXT format
2. Ask questions based on uploaded documents
3. Get answers with source references

Supported Features:
- Vector similarity search
- Keyword fallback search
- Query history tracking
- Multiple document support

File Format: Plain text (.txt)

Recommended Structure:
- Clear headings
- Paragraph breaks
- Avoid special formatting

Maximum File Size: No strict limit, but larger files take longer to process"""
    }
    
    for filename, content in examples.items():
        filepath = os.path.join("documents", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    
    print("✅ Created example documents in 'documents/' directory")

def setup_database():
    """Setup database connection test"""
    print("\nDatabase Setup:")
    print("1. Ensure your RDS PostgreSQL instance is running")
    print("2. Make sure pgvector extension is installed")
    print("3. Verify network connectivity from your ECS")
    print("\nTo install pgvector on RDS, run as admin:")
    print("   CREATE EXTENSION IF NOT EXISTS vector;")
    print("\nTest connection with: python test_connection.py")

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="AI RAG System Setup")
    parser.add_argument("--all", action="store_true", help="Run all setup steps")
    parser.add_argument("--deps", action="store_true", help="Install dependencies only")
    parser.add_argument("--env", action="store_true", help="Create .env file only")
    parser.add_argument("--docs", action="store_true", help="Create example documents")
    parser.add_argument("--db", action="store_true", help="Database setup guide")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("AI RAG System Setup")
    print("=" * 60)
    
    if args.all or (not any([args.deps, args.env, args.docs, args.db])):
        print("Running complete setup...")
        check_dependencies()
        create_env_file()
        create_example_documents()
        setup_database()
    
    elif args.deps:
        check_dependencies()
    
    elif args.env:
        create_env_file()
    
    elif args.docs:
        create_example_documents()
    
    elif args.db:
        setup_database()
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("\nNext Steps:")
    print("1. Edit .env file with your DeepSeek API key")
    print("2. Test the system: python cli_client.py --interactive")
    print("3. Run API server: python api_server.py")
    print("4. Upload documents: python cli_client.py --upload documents/machine_learning.txt")
    print("=" * 60)

if __name__ == "__main__":
    main()