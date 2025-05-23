#!/usr/bin/env python
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_agent_background import run_agent_background
from utils.logger import logger

def test_task_submission():
    """Test sending a task to the worker queue."""
    try:
        # Test parameters
        test_params = {
            "agent_run_id": "test-run-123",
            "thread_id": "test-thread-456",
            "instance_id": "test-instance",
            "project_id": "test-project-789",
            "model_name": "openai/gpt-3.5-turbo",
            "enable_thinking": False,
            "reasoning_effort": "low",
            "stream": True,
            "enable_context_manager": True
        }
        
        logger.info(f"Sending test task with params: {test_params}")
        
        # Send the task
        run_agent_background.send(**test_params)
        
        logger.info("Task sent successfully to RabbitMQ queue!")
        
    except Exception as e:
        logger.error(f"Failed to send task: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_task_submission()