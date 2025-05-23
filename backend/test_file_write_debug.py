#!/usr/bin/env python3
"""
Debug script for file write errors in Suna.
This script tests file operations directly to help diagnose issues.
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import logger
from services.supabase import DBConnection
from sandbox.sandbox import get_or_start_sandbox
from daytona_sdk import Daytona, DaytonaConfig

# Load environment variables
load_dotenv()

async def test_file_operations(project_id: str):
    """Test file operations for a given project."""
    print(f"\n=== Testing File Operations for Project: {project_id} ===\n")
    
    try:
        # Initialize database connection
        db = DBConnection()
        client = await db.client
        
        # Get project data
        print(f"1. Fetching project data...")
        project = await client.table('projects').select('*').eq('project_id', project_id).execute()
        if not project.data or len(project.data) == 0:
            print(f"❌ Project {project_id} not found")
            return
        
        project_data = project.data[0]
        sandbox_info = project_data.get('sandbox', {})
        
        if not sandbox_info.get('id'):
            print(f"❌ No sandbox found for project {project_id}")
            return
        
        sandbox_id = sandbox_info['id']
        print(f"✅ Found sandbox: {sandbox_id}")
        
        # Get or start sandbox
        print(f"\n2. Getting/starting sandbox...")
        try:
            sandbox = await get_or_start_sandbox(sandbox_id)
            print(f"✅ Sandbox is ready")
        except Exception as e:
            print(f"❌ Failed to get/start sandbox: {str(e)}")
            return
        
        # Test file operations
        test_file = f"test_write_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        test_content = "This is a test file write operation.\nTesting file write functionality."
        test_path = f"/workspace/{test_file}"
        
        print(f"\n3. Testing file write...")
        print(f"   Path: {test_path}")
        print(f"   Content size: {len(test_content)} chars")
        
        try:
            # Write file
            sandbox.fs.upload_file(test_path, test_content.encode())
            print(f"✅ File written successfully")
            
            # Verify file exists
            try:
                content = sandbox.fs.download_file(test_path)
                if content.decode() == test_content:
                    print(f"✅ File content verified")
                else:
                    print(f"⚠️  File content mismatch")
            except Exception as e:
                print(f"❌ Failed to read file back: {str(e)}")
            
            # Test permissions
            try:
                sandbox.fs.set_file_permissions(test_path, "644")
                print(f"✅ File permissions set")
            except Exception as e:
                print(f"⚠️  Failed to set permissions: {str(e)}")
            
            # Clean up
            try:
                sandbox.fs.delete_file(test_path)
                print(f"✅ Test file cleaned up")
            except Exception as e:
                print(f"⚠️  Failed to delete test file: {str(e)}")
                
        except Exception as e:
            print(f"❌ File write failed: {str(e)}")
            logger.error(f"File write error details:", exc_info=True)
        
        # Test directory creation
        print(f"\n4. Testing directory creation...")
        test_dir = f"/workspace/test_dir_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            sandbox.fs.create_folder(test_dir, "755")
            print(f"✅ Directory created: {test_dir}")
            
            # Try to create a file in the new directory
            nested_file = f"{test_dir}/nested_test.txt"
            try:
                sandbox.fs.upload_file(nested_file, b"Nested file content")
                print(f"✅ Nested file created")
                
                # Clean up
                sandbox.fs.delete_file(nested_file)
                sandbox.fs.delete_folder(test_dir)
                print(f"✅ Test directory cleaned up")
            except Exception as e:
                print(f"❌ Failed to create nested file: {str(e)}")
                
        except Exception as e:
            print(f"❌ Directory creation failed: {str(e)}")
        
        print(f"\n=== Test Complete ===\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        logger.error(f"Test error details:", exc_info=True)

async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python test_file_write_debug.py <project_id>")
        print("\nThis script tests file write operations for a given project.")
        sys.exit(1)
    
    project_id = sys.argv[1]
    await test_file_operations(project_id)

if __name__ == "__main__":
    asyncio.run(main())