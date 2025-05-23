#!/usr/bin/env python
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_agent_background import run_agent_background
from services.supabase import DBConnection
from utils.logger import logger

async def test_real_agent():
    """Test with real database entries."""
    db = DBConnection()
    await db.initialize()
    client = await db.client
    
    try:
        # Create a test project
        project_id = str(uuid.uuid4())
        project_data = {
            "id": project_id,
            "name": "Test Project",
            "account_id": "00000000-0000-0000-0000-000000000000",  # Dummy account
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await client.table('projects').insert(project_data).execute()
        logger.info(f"Created test project: {project_id}")
        
        # Create a test thread
        thread_id = str(uuid.uuid4())
        thread_data = {
            "id": thread_id,
            "project_id": project_id,
            "account_id": "00000000-0000-0000-0000-000000000000",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await client.table('threads').insert(thread_data).execute()
        logger.info(f"Created test thread: {thread_id}")
        
        # Create a test agent run
        agent_run_id = str(uuid.uuid4())
        agent_run_data = {
            "id": agent_run_id,
            "thread_id": thread_id,
            "project_id": project_id,
            "status": "queued",
            "model": "qwen3",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await client.table('agent_runs').insert(agent_run_data).execute()
        logger.info(f"Created test agent run: {agent_run_id}")
        
        # Send the task
        test_params = {
            "agent_run_id": agent_run_id,
            "thread_id": thread_id,
            "instance_id": "test-instance",
            "project_id": project_id,
            "model_name": "qwen3",
            "enable_thinking": False,
            "reasoning_effort": "low",
            "stream": True,
            "enable_context_manager": True
        }
        
        logger.info(f"Sending real task with params: {test_params}")
        run_agent_background.send(**test_params)
        logger.info("Task sent successfully!")
        
        # Wait a bit to see results
        await asyncio.sleep(5)
        
        # Check the status
        result = await client.table('agent_runs').select('status', 'error').eq('id', agent_run_id).execute()
        if result.data:
            logger.info(f"Agent run status: {result.data[0]}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            await client.table('agent_runs').delete().eq('id', agent_run_id).execute()
            await client.table('threads').delete().eq('id', thread_id).execute()
            await client.table('projects').delete().eq('id', project_id).execute()
            logger.info("Cleaned up test data")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_real_agent())