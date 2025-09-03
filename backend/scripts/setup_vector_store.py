#!/usr/bin/env python3
"""
Setup Vector Store for OpenAI Assistant
Creates a vector store and attaches all existing files to it
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')

async def main():
    """Setup vector store for the assistant"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
    
    if not api_key:
        print("❌ No OPENAI_API_KEY found in environment")
        return
    
    if not assistant_id:
        print("❌ No OPENAI_ASSISTANT_ID found in environment")
        print("   Run the cleanup script first to set an assistant ID")
        return
    
    print("🔧 Vector Store Setup Tool")
    print("=" * 80)
    print(f"📌 Assistant ID: {assistant_id}\n")
    
    client = AsyncOpenAI(
        api_key=api_key,
        default_headers={"OpenAI-Beta": "assistants=v2"}
    )
    
    try:
        # Step 1: Get the assistant
        print("1️⃣ Retrieving assistant...")
        assistant = await client.beta.assistants.retrieve(assistant_id)
        print(f"   ✅ Found: {assistant.name}")
        
        # Check current vector store status
        current_vector_store = None
        if hasattr(assistant, 'tool_resources') and assistant.tool_resources:
            if hasattr(assistant.tool_resources, 'file_search') and assistant.tool_resources.file_search:
                if hasattr(assistant.tool_resources.file_search, 'vector_store_ids'):
                    vs_ids = assistant.tool_resources.file_search.vector_store_ids
                    if vs_ids:
                        current_vector_store = vs_ids[0]
                        print(f"   ⚠️  Already has vector store: {current_vector_store}")
        
        if not current_vector_store:
            print("   ✅ No vector store attached (as expected)")
        
        # Step 2: Get all files
        print("\n2️⃣ Fetching all uploaded files...")
        files = await client.files.list(purpose="assistants")
        file_ids = [f.id for f in files.data] if files.data else []
        
        if file_ids:
            print(f"   ✅ Found {len(file_ids)} file(s):")
            for i, file in enumerate(files.data[:5], 1):
                size_mb = file.bytes / (1024*1024) if file.bytes else 0
                print(f"      {i}. {file.filename} ({size_mb:.2f} MB)")
            if len(files.data) > 5:
                print(f"      ... and {len(files.data) - 5} more")
        else:
            print("   ⚠️  No files found to attach")
        
        # Step 3: Create or update vector store
        if current_vector_store:
            print(f"\n3️⃣ Using existing vector store: {current_vector_store}")
            vector_store_id = current_vector_store
            
            # Update files in existing vector store
            if file_ids:
                print("   Adding files to existing vector store...")
                batch_size = 20
                for i in range(0, len(file_ids), batch_size):
                    batch = file_ids[i:i+batch_size]
                    await client.vector_stores.file_batches.create(
                        vector_store_id=vector_store_id,
                        file_ids=batch
                    )
                    print(f"   ✅ Added batch of {len(batch)} files")
        else:
            print("\n3️⃣ Creating new vector store...")
            vector_store = await client.vector_stores.create(
                name=f"청암 챗봇 Documents - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            vector_store_id = vector_store.id
            print(f"   ✅ Created: {vector_store_id}")
            
            # Add files to the new vector store
            if file_ids:
                print("   Adding files to vector store...")
                batch_size = 20
                for i in range(0, len(file_ids), batch_size):
                    batch = file_ids[i:i+batch_size]
                    await client.vector_stores.file_batches.create(
                        vector_store_id=vector_store_id,
                        file_ids=batch
                    )
                    print(f"   ✅ Added batch of {len(batch)} files")
        
        # Step 4: Attach vector store to assistant
        if not current_vector_store:
            print("\n4️⃣ Attaching vector store to assistant...")
            await client.beta.assistants.update(
                assistant_id=assistant_id,
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [vector_store_id]
                    }
                }
            )
            print(f"   ✅ Vector store attached successfully!")
        
        # Step 5: Verify the setup
        print("\n5️⃣ Verifying setup...")
        assistant = await client.beta.assistants.retrieve(assistant_id)
        
        if hasattr(assistant, 'tool_resources') and assistant.tool_resources:
            if hasattr(assistant.tool_resources, 'file_search') and assistant.tool_resources.file_search:
                if hasattr(assistant.tool_resources.file_search, 'vector_store_ids'):
                    vs_ids = assistant.tool_resources.file_search.vector_store_ids
                    if vs_ids and vs_ids[0] == vector_store_id:
                        print(f"   ✅ Vector store verified: {vector_store_id}")
                    else:
                        print("   ❌ Vector store not properly attached")
        
        # Step 6: Save vector store ID to .env (optional)
        print("\n6️⃣ Saving vector store ID to .env...")
        env_path = "../.env"
        
        # Read current .env
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add OPENAI_VECTOR_STORE_ID
        found = False
        for i, line in enumerate(env_lines):
            if line.startswith("OPENAI_VECTOR_STORE_ID="):
                env_lines[i] = f"OPENAI_VECTOR_STORE_ID={vector_store_id}\n"
                found = True
                break
        
        if not found:
            env_lines.append(f"\n# OpenAI Vector Store ID (auto-saved by setup script)\n")
            env_lines.append(f"OPENAI_VECTOR_STORE_ID={vector_store_id}\n")
        
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(env_lines)
        
        print(f"   ✅ Saved OPENAI_VECTOR_STORE_ID={vector_store_id}")
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ SETUP COMPLETE!")
        print(f"   • Assistant: {assistant.name}")
        print(f"   • Assistant ID: {assistant_id}")
        print(f"   • Vector Store ID: {vector_store_id}")
        print(f"   • Files indexed: {len(file_ids)}")
        print("\n🎉 Your assistant now has a properly configured vector store!")
        print("   File search capabilities are now enabled.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())