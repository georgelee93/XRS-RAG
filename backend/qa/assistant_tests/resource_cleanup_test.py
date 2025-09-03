#!/usr/bin/env python3
"""
Resource Cleanup Test for OpenAI Assistants and Vector Stores
Audits existing resources and cleans up orphaned ones
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from openai import OpenAI, AsyncOpenAI


class ResourceCleanupManager:
    def __init__(self):
        # Get API key from environment or .env file
        self.api_key = self._get_api_key()
        self.client = OpenAI(
            api_key=self.api_key,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.config_file = "assistant_config.json"
        self.backup_dir = "backups"
        
    def _get_api_key(self) -> str:
        """Get OpenAI API key from environment or .env file"""
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            # Try to load from .env file
            env_file = Path(__file__).parent.parent.parent / ".env"
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or .env file")
        
        return api_key
    
    async def audit_resources(self) -> Dict:
        """Audit all assistants and vector stores"""
        print("\n" + "="*60)
        print("RESOURCE AUDIT REPORT")
        print("="*60)
        
        audit_result = {
            "timestamp": datetime.now().isoformat(),
            "assistants": [],
            "vector_stores": [],
            "config_state": {},
            "recommendations": []
        }
        
        # List all assistants
        try:
            assistants = await self.async_client.beta.assistants.list(limit=100)
            print(f"\n📊 Found {len(assistants.data)} assistant(s)")
            
            for asst in assistants.data:
                asst_info = {
                    "id": asst.id,
                    "name": asst.name,
                    "created_at": asst.created_at,
                    "model": asst.model,
                    "has_file_search": any(tool.type == "file_search" for tool in (asst.tools or [])),
                    "vector_store_ids": []
                }
                
                # Check for attached vector stores
                if hasattr(asst, 'tool_resources') and asst.tool_resources:
                    if hasattr(asst.tool_resources, 'file_search') and asst.tool_resources.file_search:
                        if hasattr(asst.tool_resources.file_search, 'vector_store_ids'):
                            asst_info["vector_store_ids"] = asst.tool_resources.file_search.vector_store_ids
                
                audit_result["assistants"].append(asst_info)
                print(f"  • {asst.id}: {asst.name}")
                print(f"    Created: {datetime.fromtimestamp(asst.created_at).strftime('%Y-%m-%d %H:%M:%S')}")
                if asst_info["vector_store_ids"]:
                    print(f"    Vector Stores: {asst_info['vector_store_ids']}")
        
        except Exception as e:
            print(f"❌ Error listing assistants: {e}")
            audit_result["errors"] = audit_result.get("errors", []) + [str(e)]
        
        # List all vector stores using direct API call
        try:
            import httpx
            
            print(f"\n📦 Checking vector stores...")
            
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    "https://api.openai.com/v1/vector_stores",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "OpenAI-Beta": "assistants=v2"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    vector_stores_data = data.get('data', [])
                    print(f"Found {len(vector_stores_data)} vector store(s)")
                    
                    for vs in vector_stores_data:
                        vs_info = {
                            "id": vs.get("id"),
                            "name": vs.get("name"),
                            "created_at": vs.get("created_at"),
                            "file_count": vs.get("file_counts", {}).get("total", 0) if vs.get("file_counts") else 0,
                            "bytes": vs.get("usage_bytes", 0)
                        }
                        audit_result["vector_stores"].append(vs_info)
                        print(f"  • {vs_info['id']}: {vs_info['name']}")
                        print(f"    Files: {vs_info['file_count']}, Size: {vs_info['bytes']} bytes")
                else:
                    print(f"⚠️  Could not list vector stores: HTTP {response.status_code}")
        
        except Exception as e:
            print(f"❌ Error listing vector stores: {e}")
            audit_result["errors"] = audit_result.get("errors", []) + [str(e)]
        
        # Check current configuration
        config_path = Path(self.config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                audit_result["config_state"] = config
                print(f"\n📋 Current Configuration:")
                print(f"  Assistant ID: {config.get('assistant_id', 'None')}")
                print(f"  Vector Store ID: {config.get('vector_store_id', 'None')}")
        else:
            print(f"\n⚠️  No configuration file found at {self.config_file}")
        
        # Generate recommendations
        self._generate_recommendations(audit_result)
        
        return audit_result
    
    def _generate_recommendations(self, audit_result: Dict):
        """Generate cleanup recommendations"""
        assistants = audit_result["assistants"]
        vector_stores = audit_result["vector_stores"]
        config = audit_result["config_state"]
        
        print("\n🔍 Analysis & Recommendations:")
        print("-"*40)
        
        # Check for multiple assistants
        if len(assistants) > 1:
            print(f"⚠️  Multiple assistants detected ({len(assistants)})")
            audit_result["recommendations"].append("Clean up duplicate assistants")
            
            # Identify keeper
            keeper = self._identify_keeper_assistant(assistants, config)
            if keeper:
                print(f"  Recommended keeper: {keeper['id']} ({keeper['name']})")
                audit_result["keeper_assistant"] = keeper
        elif len(assistants) == 1:
            print("✅ Single assistant found (expected)")
            audit_result["keeper_assistant"] = assistants[0]
        else:
            print("❌ No assistants found - will need to create one")
        
        # Check for multiple vector stores
        if len(vector_stores) > 1:
            print(f"⚠️  Multiple vector stores detected ({len(vector_stores)})")
            audit_result["recommendations"].append("Clean up duplicate vector stores")
            
            # Identify keeper
            keeper_vs = self._identify_keeper_vector_store(vector_stores, audit_result.get("keeper_assistant"))
            if keeper_vs:
                print(f"  Recommended keeper: {keeper_vs['id']} ({keeper_vs['name']})")
                audit_result["keeper_vector_store"] = keeper_vs
        elif len(vector_stores) == 1:
            print("✅ Single vector store found (expected)")
            audit_result["keeper_vector_store"] = vector_stores[0]
        else:
            print("⚠️  No vector stores found")
        
        # Check configuration integrity
        if config:
            config_asst = config.get("assistant_id")
            config_vs = config.get("vector_store_id")
            
            if config_asst and not any(a["id"] == config_asst for a in assistants):
                print(f"❌ Config references non-existent assistant: {config_asst}")
                audit_result["recommendations"].append("Update config with valid assistant ID")
            
            if config_vs and config_vs != "null" and not any(v["id"] == config_vs for v in vector_stores):
                print(f"❌ Config references non-existent vector store: {config_vs}")
                audit_result["recommendations"].append("Update config with valid vector store ID")
            
            if not config_vs or config_vs == "null":
                print("⚠️  Config has null vector_store_id")
                audit_result["recommendations"].append("Create and attach vector store")
    
    def _identify_keeper_assistant(self, assistants: List[Dict], config: Dict) -> Optional[Dict]:
        """Identify which assistant to keep"""
        # Priority 1: Assistant in config (if valid)
        config_id = config.get("assistant_id") if config else None
        if config_id:
            for asst in assistants:
                if asst["id"] == config_id:
                    return asst
        
        # Priority 2: Assistant with vector store attached
        for asst in assistants:
            if asst.get("vector_store_ids"):
                return asst
        
        # Priority 3: Most recently created
        if assistants:
            return max(assistants, key=lambda x: x["created_at"])
        
        return None
    
    def _identify_keeper_vector_store(self, vector_stores: List[Dict], keeper_assistant: Optional[Dict]) -> Optional[Dict]:
        """Identify which vector store to keep"""
        if not vector_stores:
            return None
        
        # Priority 1: Vector store attached to keeper assistant
        if keeper_assistant and keeper_assistant.get("vector_store_ids"):
            for vs_id in keeper_assistant["vector_store_ids"]:
                for vs in vector_stores:
                    if vs["id"] == vs_id:
                        return vs
        
        # Priority 2: Vector store with most files
        vs_with_files = [vs for vs in vector_stores if vs.get("file_count", 0) > 0]
        if vs_with_files:
            return max(vs_with_files, key=lambda x: x["file_count"])
        
        # Priority 3: Most recently created
        return max(vector_stores, key=lambda x: x["created_at"])
    
    async def backup_configuration(self, audit_result: Dict):
        """Backup current configuration and audit results"""
        os.makedirs(self.backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{self.backup_dir}/backup_{timestamp}.json"
        
        with open(backup_file, 'w') as f:
            json.dump(audit_result, f, indent=2)
        
        print(f"\n💾 Backup saved to: {backup_file}")
        
        # Also backup current config if it exists
        if os.path.exists(self.config_file):
            config_backup = f"{self.backup_dir}/assistant_config_{timestamp}.json"
            with open(self.config_file, 'r') as src:
                with open(config_backup, 'w') as dst:
                    dst.write(src.read())
            print(f"💾 Config backup saved to: {config_backup}")
    
    async def cleanup_resources(self, audit_result: Dict, dry_run: bool = False):
        """Clean up orphaned resources"""
        print("\n" + "="*60)
        print("RESOURCE CLEANUP" + (" (DRY RUN)" if dry_run else ""))
        print("="*60)
        
        keeper_assistant = audit_result.get("keeper_assistant")
        keeper_vector_store = audit_result.get("keeper_vector_store")
        
        if not keeper_assistant:
            print("❌ No keeper assistant identified. Skipping cleanup.")
            return False
        
        cleanup_log = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "deleted_assistants": [],
            "deleted_vector_stores": [],
            "kept_assistant": keeper_assistant["id"] if keeper_assistant else None,
            "kept_vector_store": keeper_vector_store["id"] if keeper_vector_store else None
        }
        
        # Delete orphaned assistants
        for asst in audit_result["assistants"]:
            if asst["id"] != keeper_assistant["id"]:
                print(f"\n🗑️  Deleting assistant: {asst['id']} ({asst['name']})")
                if not dry_run:
                    try:
                        await self.async_client.beta.assistants.delete(asst["id"])
                        print(f"  ✅ Deleted successfully")
                        cleanup_log["deleted_assistants"].append(asst["id"])
                    except Exception as e:
                        print(f"  ❌ Error: {e}")
                else:
                    print(f"  [DRY RUN] Would delete")
                    cleanup_log["deleted_assistants"].append(asst["id"])
        
        # Delete orphaned vector stores
        if keeper_vector_store:
            for vs in audit_result["vector_stores"]:
                if vs["id"] != keeper_vector_store["id"]:
                    print(f"\n🗑️  Deleting vector store: {vs['id']} ({vs['name']})")
                    if not dry_run:
                        try:
                            # Use direct API call to delete vector store
                            import httpx
                            async with httpx.AsyncClient() as http_client:
                                response = await http_client.delete(
                                    f"https://api.openai.com/v1/vector_stores/{vs['id']}",
                                    headers={
                                        "Authorization": f"Bearer {self.api_key}",
                                        "OpenAI-Beta": "assistants=v2"
                                    }
                                )
                                if response.status_code in [200, 204]:
                                    print(f"  ✅ Deleted successfully")
                                    cleanup_log["deleted_vector_stores"].append(vs["id"])
                                else:
                                    print(f"  ❌ Error: HTTP {response.status_code}")
                        except Exception as e:
                            print(f"  ❌ Error: {e}")
                    else:
                        print(f"  [DRY RUN] Would delete")
                        cleanup_log["deleted_vector_stores"].append(vs["id"])
        
        # Update configuration
        print("\n📝 Updating configuration...")
        new_config = {
            "assistant_id": keeper_assistant["id"],
            "vector_store_id": keeper_vector_store["id"] if keeper_vector_store else None,
            "created_at": audit_result["config_state"].get("created_at", datetime.now().isoformat()),
            "last_updated": datetime.now().isoformat(),
            "last_cleanup": datetime.now().isoformat()
        }
        
        if not dry_run:
            with open(self.config_file, 'w') as f:
                json.dump(new_config, f, indent=2)
            print(f"  ✅ Configuration updated")
        else:
            print(f"  [DRY RUN] Would update config with:")
            print(f"    assistant_id: {new_config['assistant_id']}")
            print(f"    vector_store_id: {new_config['vector_store_id']}")
        
        # Save cleanup log
        cleanup_log_file = f"{self.backup_dir}/cleanup_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(self.backup_dir, exist_ok=True)
        with open(cleanup_log_file, 'w') as f:
            json.dump(cleanup_log, f, indent=2)
        print(f"\n📄 Cleanup log saved to: {cleanup_log_file}")
        
        # Summary
        print("\n" + "="*60)
        print("CLEANUP SUMMARY")
        print("="*60)
        print(f"Deleted {len(cleanup_log['deleted_assistants'])} assistant(s)")
        print(f"Deleted {len(cleanup_log['deleted_vector_stores'])} vector store(s)")
        print(f"Kept assistant: {cleanup_log['kept_assistant']}")
        print(f"Kept vector store: {cleanup_log['kept_vector_store']}")
        
        return True
    
    async def verify_cleanup(self):
        """Verify cleanup was successful"""
        print("\n" + "="*60)
        print("POST-CLEANUP VERIFICATION")
        print("="*60)
        
        # Re-audit resources
        audit_result = await self.audit_resources()
        
        assistants = audit_result["assistants"]
        vector_stores = audit_result["vector_stores"]
        
        # Verify counts
        success = True
        
        if len(assistants) == 1:
            print("✅ Exactly 1 assistant remaining")
        else:
            print(f"❌ Expected 1 assistant, found {len(assistants)}")
            success = False
        
        if len(vector_stores) <= 1:
            print(f"✅ {len(vector_stores)} vector store(s) remaining (expected ≤1)")
        else:
            print(f"❌ Expected ≤1 vector store, found {len(vector_stores)}")
            success = False
        
        # Verify configuration
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            if config.get("assistant_id") and config["assistant_id"] == assistants[0]["id"]:
                print("✅ Configuration has correct assistant ID")
            else:
                print("❌ Configuration assistant ID mismatch")
                success = False
            
            if vector_stores and config.get("vector_store_id") == vector_stores[0]["id"]:
                print("✅ Configuration has correct vector store ID")
            elif not vector_stores and not config.get("vector_store_id"):
                print("⚠️  No vector store (will be created on next use)")
            else:
                print("❌ Configuration vector store ID mismatch")
                success = False
        
        return success


async def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit and cleanup OpenAI assistants and vector stores")
    parser.add_argument("--auto-cleanup", action="store_true", help="Automatically cleanup without prompting")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be deleted")
    args = parser.parse_args()
    
    manager = ResourceCleanupManager()
    
    try:
        # Step 1: Audit current state
        print("Step 1: Auditing current resources...")
        audit_result = await manager.audit_resources()
        
        # Step 2: Backup configuration
        print("\nStep 2: Creating backup...")
        await manager.backup_configuration(audit_result)
        
        # Step 3: Perform cleanup (dry run first)
        if len(audit_result["assistants"]) > 1 or len(audit_result["vector_stores"]) > 1:
            if args.dry_run:
                print("\nStep 3: Performing DRY RUN only...")
                await manager.cleanup_resources(audit_result, dry_run=True)
                print("\n⏭️  Dry run complete (no actual changes made)")
            elif args.auto_cleanup:
                print("\nStep 3: Performing automatic cleanup...")
                await manager.cleanup_resources(audit_result, dry_run=False)
                
                # Step 4: Verify cleanup
                print("\nStep 4: Verifying cleanup...")
                success = await manager.verify_cleanup()
                
                if success:
                    print("\n✅ Cleanup completed successfully!")
                else:
                    print("\n⚠️  Cleanup completed with warnings")
            else:
                print("\nStep 3: Cleanup needed - performing dry run...")
                await manager.cleanup_resources(audit_result, dry_run=True)
                
                # Ask for confirmation
                print("\n" + "="*60)
                print("To proceed with cleanup, run with --auto-cleanup flag")
                print("Example: python3 resource_cleanup_test.py --auto-cleanup")
        else:
            print("\n✅ No cleanup needed - resources already optimized")
            
            # Still verify configuration
            if not audit_result["config_state"].get("vector_store_id") or audit_result["config_state"].get("vector_store_id") == "null":
                print("\n⚠️  Configuration needs vector_store_id update")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)