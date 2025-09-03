#!/usr/bin/env python3
"""
Demonstration of how the RAG Chatbot test flow works
Shows each step clearly with explanations
"""

import asyncio
import aiohttp
import json
import uuid
from datetime import datetime
from pathlib import Path

class RAGTestFlowDemo:
    """Demonstrates the test flow for RAG Chatbot"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.session_id = str(uuid.uuid4())
        
    async def demonstrate_flow(self):
        """Demonstrate the complete test flow"""
        print("=" * 60)
        print("RAG CHATBOT TEST FLOW DEMONSTRATION")
        print("=" * 60)
        print()
        print("This demonstration shows how the testing works step by step")
        print()
        
        # Step 1: Test Backend Health
        print("━" * 60)
        print("STEP 1: Verify Backend is Running")
        print("━" * 60)
        print("→ Checking /api/health endpoint...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Backend is healthy: {data}")
                else:
                    print(f"❌ Backend unhealthy: Status {resp.status}")
                    return
        
        print()
        
        # Step 2: List Current Documents
        print("━" * 60)
        print("STEP 2: Check Existing Documents")
        print("━" * 60)
        print("→ Fetching document list from /api/documents...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/documents") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    docs = data.get("documents", [])
                    print(f"✅ Found {len(docs)} existing documents:")
                    for doc in docs[:3]:  # Show first 3
                        print(f"   - {doc.get('name', 'Unnamed')}")
                        print(f"     ID: {doc.get('id', 'N/A')}")
                        print(f"     Size: {doc.get('size', 0)} bytes")
                else:
                    print(f"❌ Failed to get documents: Status {resp.status}")
        
        print()
        
        # Step 3: Test Chat Functionality
        print("━" * 60)
        print("STEP 3: Test Chat API")
        print("━" * 60)
        print(f"→ Sending test message with session ID: {self.session_id[:8]}...")
        
        test_message = "Hello, this is a test. What documents do you have access to?"
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "message": test_message,
                "session_id": self.session_id
            }
            
            print(f"   Request: '{test_message}'")
            print("   Waiting for AI response...")
            
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        response_preview = data.get("response", "")[:200]
                        print(f"✅ Chat working! Response preview:")
                        print(f"   '{response_preview}...'")
                        print(f"   Response time: {data.get('duration_seconds', 0):.2f}s")
                    else:
                        print(f"❌ Chat failed: {data.get('error')}")
                else:
                    print(f"❌ Chat request failed: Status {resp.status}")
        
        print()
        
        # Step 4: Explain Document Upload Process
        print("━" * 60)
        print("STEP 4: Document Upload Process (Explanation)")
        print("━" * 60)
        print("When a document is uploaded, the following happens:")
        print()
        print("1. FILE UPLOAD:")
        print("   Client → Backend API (/api/documents/upload)")
        print("   ↓")
        print("2. OPENAI STORAGE:")
        print("   Backend → OpenAI Files API")
        print("   - File gets uploaded to OpenAI")
        print("   - Returns file_id (e.g., 'file-abc123')")
        print("   ↓")
        print("3. VECTOR STORE:")
        print("   Backend → OpenAI Vector Store")
        print("   - File added to assistant's vector store")
        print("   - Enables semantic search")
        print("   ↓")
        print("4. SUPABASE STORAGE:")
        print("   Backend → Supabase Storage Bucket")
        print("   - File saved for download functionality")
        print("   - Path: /documents/[filename]")
        print("   ↓")
        print("5. DATABASE RECORDING:")
        print("   Backend → Supabase Database")
        print("   - document_registry table updated")
        print("   - Records: file_id, name, size, created_at")
        
        print()
        
        # Step 5: Explain Vector Store Integrity
        print("━" * 60)
        print("STEP 5: Vector Store Integrity Check (Explanation)")
        print("━" * 60)
        print("The system should maintain:")
        print()
        print("1. SINGLE ASSISTANT:")
        print("   - Only one assistant named '청암 RAG 챗봇'")
        print("   - No duplicates created")
        print()
        print("2. VECTOR STORE CONNECTION:")
        print("   - Assistant connected to exactly one vector store")
        print("   - Vector store contains all uploaded documents")
        print()
        print("3. NO ORPHANED STORES:")
        print("   - No 'untitled' vector stores")
        print("   - All stores properly named and attached")
        print()
        print("This was previously an issue where file attachments")
        print("to messages would create new 'untitled' vector stores.")
        print("Fixed by removing attachments from messages.")
        
        print()
        
        # Step 6: Explain Usage Tracking
        print("━" * 60)
        print("STEP 6: Usage Tracking (Explanation)")
        print("━" * 60)
        print("Every interaction is tracked in Supabase:")
        print()
        print("1. CHAT MESSAGES TABLE:")
        print("   - id (UUID)")
        print("   - session_id (UUID)")
        print("   - role (user/assistant)")
        print("   - content (message text)")
        print("   - created_at (timestamp)")
        print()
        print("2. USAGE TRACKING TABLE:")
        print("   - user_id")
        print("   - user_email")
        print("   - operation (chat/upload/delete)")
        print("   - tokens_used")
        print("   - duration_seconds")
        print()
        print("3. DOCUMENT USAGE TABLE:")
        print("   - file_id")
        print("   - access_count")
        print("   - last_accessed")
        
        print()
        
        # Summary
        print("=" * 60)
        print("TEST FLOW SUMMARY")
        print("=" * 60)
        print()
        print("The comprehensive test verifies:")
        print("✓ Backend API is running and healthy")
        print("✓ Documents can be uploaded and stored correctly")
        print("✓ Chat can access and retrieve document information")
        print("✓ No duplicate assistants or orphaned vector stores")
        print("✓ All interactions are properly logged in database")
        print()
        print("Each test ensures the system works end-to-end,")
        print("from user interaction to AI response to data persistence.")


async def main():
    """Run the demonstration"""
    demo = RAGTestFlowDemo()
    await demo.demonstrate_flow()


if __name__ == "__main__":
    asyncio.run(main())