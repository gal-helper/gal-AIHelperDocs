import asyncio
import sys
import os
import argparse
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_processor import rag_processor

class CLIClient:
    
    def __init__(self):
        self.rag = rag_processor
    
    async def initialize(self) -> bool:
        print("Initializing AI RAG system...")
        return await self.rag.initialize()
    
    async def upload_document(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}")
            return
        
        print(f"Processing document: {filepath}")
        result = await self.rag.process_document(filepath)
        
        if result["success"]:
            print(f"Successfully processed: {result['filename']}")
            print(f"   Documents processed: {result['documents_processed']}")
            print(f"   Document IDs: {result.get('document_ids', [])}")
            print(f"   Message: {result['message']}")
        else:
            print(f"Failed to process: {result.get('message', 'Unknown error')}")
    
    async def ask_question(self, question: str, use_rag: bool = True) -> None:
        print(f"\nQuestion: {question}")
        print("Thinking...")
        
        result = await self.rag.ask_question(question, use_rag)
        
        print(f"\nAnswer ({result['response_time']:.2f}s):")
        print("-" * 80)
        print(result["answer"])
        print("-" * 80)
        
        if result.get("sources"):
            print(f"\nSources ({len(result['sources'])}):")
            for i, source in enumerate(result["sources"], 1):
                similarity = source.get("similarity", 0)
                sim_str = f"{similarity:.1%}" if isinstance(similarity, (int, float)) else "N/A"
                print(f"{i}. {source['filename']} (Similarity: {sim_str})")
                print(f"   {source['content'][:100]}...")
        else:
            print("\nNo sources used (direct AI response)")
    
    async def show_stats(self) -> None:
        print("\nSystem Statistics:")
        print("=" * 60)
        
        stats = await self.rag.get_stats()
        
        if "error" in stats:
            print(f"Error getting stats: {stats['error']}")
            return
        
        print(f"Documents in database: {stats.get('documents', 0)}")
        print(f"Vectorized documents: {stats.get('vectorized_documents', 0)}")
        print(f"Total queries: {stats.get('queries', 0)}")
        
        if stats.get('file_types'):
            print(f"\nFile types:")
            for file_type, count in stats['file_types'].items():
                print(f"  {file_type}: {count}")
        
        if stats.get('recent_queries'):
            print(f"\nRecent queries ({len(stats['recent_queries'])}):")
            for query in stats['recent_queries'][:5]:
                print(f"  - {query['question']}")
                print(f"    At: {query['asked_at']}")
    
    async def interactive_mode(self) -> None:
        print("\n" + "=" * 60)
        print("AI RAG System - Interactive Mode")
        print("=" * 60)
        print("Commands:")
        print("  /help     - Show this help")
        print("  /stats    - Show system statistics")
        print("  /upload   - Upload a document")
        print("  /mode     - Toggle RAG mode")
        print("  /exit     - Exit the program")
        print("\nJust type your question to ask.")
        print("=" * 60)
        
        use_rag = True
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == '/exit':
                    print("Goodbye!")
                    break
                
                elif user_input.lower() == '/help':
                    print("Available commands:")
                    print("  /help     - Show help")
                    print("  /stats    - Show statistics")
                    print("  /upload   - Upload document")
                    print("  /mode     - Toggle RAG mode")
                    print("  /exit     - Exit")
                    continue
                
                elif user_input.lower() == '/stats':
                    await self.show_stats()
                    continue
                
                elif user_input.lower() == '/upload':
                    filepath = input("Enter file path: ").strip()
                    if filepath:
                        await self.upload_document(filepath)
                    continue
                
                elif user_input.lower() == '/mode':
                    use_rag = not use_rag
                    mode = "RAG" if use_rag else "Direct AI"
                    print(f"Mode changed to: {mode}")
                    continue
                
                await self.ask_question(user_input, use_rag)
                
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

async def main():
    parser = argparse.ArgumentParser(description="AI RAG System CLI")
    parser.add_argument("--question", "-q", help="Ask a single question")
    parser.add_argument("--upload", "-u", help="Upload a document")
    parser.add_argument("--stats", "-s", action="store_true", help="Show statistics")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--rag", action="store_true", default=True, help="Use RAG (default)")
    parser.add_argument("--direct", action="store_true", help="Use direct AI (no RAG)")
    
    args = parser.parse_args()
    
    client = CLIClient()
    
    if not await client.initialize():
        print("Failed to initialize system. Please check configuration.")
        return
    
    if args.upload:
        await client.upload_document(args.upload)
    
    elif args.question:
        use_rag = args.rag and not args.direct
        await client.ask_question(args.question, use_rag)
    
    elif args.stats:
        await client.show_stats()
    
    elif args.interactive:
        await client.interactive_mode()
    
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())