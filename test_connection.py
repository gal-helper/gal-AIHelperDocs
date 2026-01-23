# test_connection.py - Test all connections for Alibaba DashScope
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from ai_service import ai_service
from database import db_service

async def test_ai_connection():
    """Test Alibaba DashScope API connection"""
    print("\n[1/3] Testing Alibaba DashScope API...")
    
    # Check if API key is configured
    if config.DASHSCOPE_API_KEY == "sk-your-dashscope-api-key-here":
        print("❌ Please set your Alibaba DashScope API key in config.py")
        print("   Get API key from: https://dashscope.console.aliyun.com/apiKey")
        return False
    
    try:
        # Test embedding
        test_text = "Test connection to Alibaba DashScope"
        embedding = await ai_service.get_embedding(test_text)
        
        print(f"✅ Embedding generated: {len(embedding)} dimensions")
        
        # Test chat
        response = await ai_service.chat_completion([
            {"role": "user", "content": "Say hello in one word"}
        ])
        
        print(f"✅ Chat response: {response}")
        return True
    except Exception as e:
        print(f"❌ AI connection failed: {e}")
        print("   This could be due to:")
        print("   1. Invalid API key")
        print("   2. Network issues (ECS cannot access dashscope.aliyuncs.com)")
        print("   3. Insufficient account balance")
        return False

async def test_database_connection():
    """Test database connection"""
    print("\n[2/3] Testing Database Connection...")
    
    try:
        connected = await db_service.connect()
        if not connected:
            print("❌ Database connection failed")
            return False
        
        print("✅ Database connected successfully")
        
        # Test table creation
        initialized = await db_service.initialize_tables()
        if initialized:
            print("✅ Database tables initialized")
        else:
            print("⚠️  Table initialization had issues")
        
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_system_integration():
    """Test complete system integration"""
    print("\n[3/3] Testing System Integration...")
    
    try:
        # Import after dependencies are tested
        from rag_processor import rag_processor
        
        initialized = await rag_processor.initialize()
        if not initialized:
            print("❌ System initialization failed")
            return False
        
        print("✅ System initialized successfully")
        
        # Get statistics
        stats = await rag_processor.get_stats()
        if "error" not in stats:
            print(f"✅ System stats: {stats.get('documents', 0)} documents, {stats.get('chunks', 0)} chunks")
        else:
            print(f"⚠️  Could not get stats: {stats.get('error')}")
        
        return True
    except Exception as e:
        print(f"❌ System integration failed: {e}")
        return False

async def test_network_connectivity():
    """Test network connectivity to Alibaba services"""
    print("\n[0/3] Testing Network Connectivity...")
    
    import socket
    import aiohttp
    
    test_endpoints = [
        ("dashscope.aliyuncs.com", 443),
        ("api.deepseek.com", 443),
        (config.DB_HOST, config.DB_PORT)
    ]
    
    all_accessible = True
    for host, port in test_endpoints:
        try:
            # Test TCP connection
            reader, writer = await asyncio.open_connection(host, port, ssl=(port==443))
            writer.close()
            await writer.wait_closed()
            print(f"✅ {host}:{port} is accessible")
        except Exception as e:
            print(f"❌ Cannot connect to {host}:{port} - {e}")
            all_accessible = False
    
    return all_accessible

async def main():
    """Main test function"""
    print("=" * 60)
    print("AI RAG System Connection Test (Alibaba DashScope)")
    print("=" * 60)
    
    # First test network
    network_ok = await test_network_connectivity()
    if not network_ok:
        print("\n⚠️  Network connectivity issues detected")
        print("   Your ECS may have network restrictions")
        print("   Please check security groups and network ACLs")
    
    # Then test the services
    ai_ok = await test_ai_connection()
    db_ok = await test_database_connection()
    system_ok = await test_system_integration()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"Network: {'✅ PASS' if network_ok else '❌ FAIL'}")
    print(f"Alibaba DashScope API: {'✅ PASS' if ai_ok else '❌ FAIL'}")
    print(f"Database: {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"System Integration: {'✅ PASS' if system_ok else '❌ FAIL'}")
    
    if ai_ok and db_ok and system_ok:
        print("\n🎉 All tests passed! System is ready.")
        print("\nYou can now:")
        print("1. Run interactive CLI: python cli_client.py --interactive")
        print("2. Start API server: python api_server.py")
        print("3. Upload documents: python cli_client.py --upload <file.txt>")
    else:
        print("\n⚠️  Some tests failed. Please check:")
        if not ai_ok:
            print("  - Alibaba DashScope API key in config.py")
            print("  - Visit: https://dashscope.console.aliyun.com/apiKey")
            print("  - Network connectivity to dashscope.aliyuncs.com")
        if not db_ok:
            print("  - Database credentials in config.py")
            print("  - RDS instance status and network access")
            print("  - pgvector extension installation")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())