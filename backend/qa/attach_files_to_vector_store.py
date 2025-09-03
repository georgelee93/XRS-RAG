#!/usr/bin/env python3
"""
Script to attach existing documents to the vector store
This fixes the issue where the vector store has 0 files attached
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from openai import OpenAI
import httpx


class VectorStoreFileAttacher:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.client = OpenAI(
            api_key=self.api_key,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.config = self._load_config()
        
    def _get_api_key(self) -> str:
        """Get OpenAI API key from environment or .env file"""
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            env_file = Path(__file__).parent.parent / ".env"
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        return api_key
    
    def _load_config(self) -> Dict:
        """Load assistant configuration"""
        config_file = Path(__file__).parent.parent / "assistant_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            raise ValueError("assistant_config.json not found")
    
    async def get_documents_from_storage(self) -> List[Dict]:
        """Get all documents from Supabase storage via API"""
        print("\n📁 Fetching documents from storage...")
        
        # Get auth token and make API call
        from auth_helper import get_auth_token, get_auth_headers
        
        token = await get_auth_token()
        headers = get_auth_headers(token)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'http://localhost:8080/api/documents',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                print(f"  Found {len(documents)} documents in storage")
                
                for doc in documents:
                    print(f"  - {doc.get('filename', 'Unknown')}")
                    if 'openai_file_id' in doc:
                        print(f"    OpenAI File ID: {doc['openai_file_id']}")
                
                return documents
            else:
                print(f"  ❌ Failed to fetch documents: HTTP {response.status_code}")
                return []
    
    def check_vector_store_status(self):
        """Check current vector store status"""
        print("\n📦 Checking vector store status...")
        vector_store_id = self.config.get('vector_store_id')
        
        if not vector_store_id:
            print("  ❌ No vector store ID in configuration")
            return None
        
        try:
            # Get vector store details using HTTP API
            import httpx
            with httpx.Client() as http_client:
                response = http_client.get(
                    f"https://api.openai.com/v1/vector_stores/{vector_store_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "OpenAI-Beta": "assistants=v2"
                    }
                )
                
                if response.status_code == 200:
                    vs_data = response.json()
                    print(f"  Vector Store ID: {vector_store_id}")
                    print(f"  Name: {vs_data.get('name', 'Unnamed')}")
                    print(f"  File counts: {vs_data.get('file_counts', {})}")
                    
                    # Get files in vector store
                    files_response = http_client.get(
                        f"https://api.openai.com/v1/vector_stores/{vector_store_id}/files",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "OpenAI-Beta": "assistants=v2"
                        }
                    )
                    
                    if files_response.status_code == 200:
                        files_data = files_response.json()
                        attached_files = files_data.get('data', [])
                        print(f"  Currently attached files: {len(attached_files)}")
                        for file in attached_files[:5]:  # Show first 5
                            print(f"    - {file['id']}")
                        if len(attached_files) > 5:
                            print(f"    ... and {len(attached_files) - 5} more")
                        return attached_files
                    else:
                        print(f"  ❌ Failed to get files: HTTP {files_response.status_code}")
                        return []
                else:
                    print(f"  ❌ Vector store not accessible: HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"  ❌ Error checking vector store: {e}")
            return None
    
    async def upload_and_attach_files(self, documents: List[Dict]):
        """Attach existing file IDs to vector store"""
        print("\n🔄 Attaching files to vector store...")
        
        vector_store_id = self.config.get('vector_store_id')
        if not vector_store_id:
            print("  ❌ No vector store ID in configuration")
            return False
        
        file_ids_to_attach = []
        
        # Collect all file IDs from documents
        for doc in documents:
            if 'openai_file_id' in doc and doc['openai_file_id']:
                print(f"  ✅ {doc.get('filename', 'Unknown')} has file ID: {doc['openai_file_id']}")
                file_ids_to_attach.append(doc['openai_file_id'])
            else:
                print(f"  ⚠️  {doc.get('filename', 'Unknown')} has no file ID - skipping")
        
        # Now attach all files to the vector store
        if file_ids_to_attach:
            print(f"\n📎 Attaching {len(file_ids_to_attach)} files to vector store...")
            
            import httpx
            with httpx.Client() as http_client:
                for file_id in file_ids_to_attach:
                    try:
                        response = http_client.post(
                            f"https://api.openai.com/v1/vector_stores/{vector_store_id}/files",
                            headers={
                                "Authorization": f"Bearer {self.api_key}",
                                "OpenAI-Beta": "assistants=v2",
                                "Content-Type": "application/json"
                            },
                            json={"file_id": file_id}
                        )
                        
                        if response.status_code == 200:
                            print(f"    ✅ Attached {file_id}")
                        else:
                            print(f"    ❌ Failed to attach {file_id}: HTTP {response.status_code}")
                            if response.text:
                                print(f"       Error: {response.text[:200]}")
                                
                    except Exception as e:
                        print(f"    ❌ Error attaching {file_id}: {e}")
            
            return True
        else:
            print("  ⚠️  No files to attach")
            return False
    
    def verify_attachment(self):
        """Verify files are attached to vector store"""
        print("\n✅ Verifying attachment...")
        attached_files = self.check_vector_store_status()
        
        if attached_files is not None:
            if len(attached_files) > 0:
                print(f"  ✅ SUCCESS: {len(attached_files)} files attached to vector store")
                return True
            else:
                print("  ❌ No files attached to vector store")
                return False
        else:
            print("  ❌ Could not verify attachment")
            return False
    
    async def run(self):
        """Main execution"""
        print("="*60)
        print("VECTOR STORE FILE ATTACHMENT SCRIPT")
        print("="*60)
        
        # Check initial status
        self.check_vector_store_status()
        
        # Get documents from storage
        documents = await self.get_documents_from_storage()
        
        if not documents:
            print("\n❌ No documents found in storage")
            return False
        
        # Upload and attach files
        success = await self.upload_and_attach_files(documents)
        
        if success:
            # Verify attachment
            self.verify_attachment()
        
        print("\n" + "="*60)
        print("COMPLETE")
        print("="*60)
        
        return success


async def main():
    """Main entry point"""
    attacher = VectorStoreFileAttacher()
    success = await attacher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())