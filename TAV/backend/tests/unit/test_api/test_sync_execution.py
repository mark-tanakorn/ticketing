#!/usr/bin/env python3
"""
Test script for synchronous workflow execution modes.

Usage:
    python test_sync_execution.py <workflow_id> <mode>

Modes:
    async       - Async mode (default, returns immediately)
    sync        - Sync mode (waits for completion, 5min timeout)
    timeout30   - Sync mode with 30s timeout
    timeout60   - Sync mode with 60s timeout
"""

import sys
import time
import requests
import json
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = None  # Set your API key or use None for no auth

def get_headers(await_completion: Optional[str] = None):
    """Get request headers with optional X-Await-Completion"""
    headers = {
        "Content-Type": "application/json"
    }
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if await_completion:
        headers["X-Await-Completion"] = await_completion
    return headers

def execute_workflow_async(workflow_id: str):
    """Execute workflow in async mode (default)"""
    print("=" * 60)
    print("MODE: ASYNC (returns immediately)")
    print("=" * 60)
    
    start_time = time.time()
    
    response = requests.post(
        f"{BASE_URL}/api/v1/workflows/{workflow_id}/execute",
        headers=get_headers(),
        json={
            "initial_data": {
                "test_mode": "async",
                "timestamp": time.time()
            }
        }
    )
    
    response_time = time.time() - start_time
    
    print(f"Response time: {response_time:.3f}s")
    print(f"Status code: {response.status_code}")
    print()
    
    result = response.json()
    print("Response:")
    print(json.dumps(result, indent=2))
    print()
    
    if result.get("execution_id"):
        execution_id = result["execution_id"]
        print(f"Execution ID: {execution_id}")
        print("Poll for results at:")
        print(f"  GET {BASE_URL}/api/v1/executions/{execution_id}")
        
        # Optional: Poll for results
        print("\nPolling for results (max 60s)...")
        poll_start = time.time()
        while time.time() - poll_start < 60:
            time.sleep(2)
            status_response = requests.get(
                f"{BASE_URL}/api/v1/executions/{execution_id}",
                headers=get_headers()
            )
            status = status_response.json()
            
            print(f"  Status: {status.get('status')} ({time.time() - poll_start:.1f}s)")
            
            if status.get("status") in ["completed", "failed"]:
                print("\n✅ Execution completed!")
                print("Final outputs:")
                print(json.dumps(status.get("final_outputs"), indent=2))
                break
        else:
            print("\n⏱️ Polling timeout (60s)")

def execute_workflow_sync(workflow_id: str, timeout: Optional[int] = None):
    """Execute workflow in sync mode (waits for completion)"""
    print("=" * 60)
    if timeout:
        print(f"MODE: SYNC with {timeout}s timeout")
    else:
        print("MODE: SYNC (waits for completion, max 300s)")
    print("=" * 60)
    
    start_time = time.time()
    
    await_completion = f"timeout={timeout}" if timeout else "true"
    
    response = requests.post(
        f"{BASE_URL}/api/v1/workflows/{workflow_id}/execute",
        headers=get_headers(await_completion),
        json={
            "initial_data": {
                "test_mode": f"sync_{timeout}" if timeout else "sync",
                "timestamp": time.time()
            }
        }
    )
    
    response_time = time.time() - start_time
    
    print(f"Response time: {response_time:.3f}s")
    print(f"Status code: {response.status_code}")
    print()
    
    result = response.json()
    print("Response:")
    print(json.dumps(result, indent=2))
    print()
    
    # Analyze result
    if result.get("timeout_exceeded"):
        print("⏱️ TIMEOUT EXCEEDED")
        print(f"Workflow is still running after {timeout or 300}s")
        print(f"Execution ID: {result.get('execution_id')}")
        print("You can poll for results using:")
        print(f"  GET {BASE_URL}/api/v1/executions/{result['execution_id']}")
    elif result.get("status") == "completed":
        print("✅ EXECUTION COMPLETED")
        print(f"Duration: {result.get('duration_seconds', 0):.2f}s")
        if result.get("final_outputs"):
            print("\nFinal Outputs:")
            print(json.dumps(result["final_outputs"], indent=2))
    elif result.get("status") == "failed":
        print("❌ EXECUTION FAILED")
        print(f"Error: {result.get('error_message', 'Unknown error')}")
    else:
        print(f"Status: {result.get('status')}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    workflow_id = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "async"
    
    print(f"\nWorkflow ID: {workflow_id}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    try:
        if mode == "async":
            execute_workflow_async(workflow_id)
        elif mode == "sync":
            execute_workflow_sync(workflow_id)
        elif mode.startswith("timeout"):
            timeout = int(mode.replace("timeout", ""))
            execute_workflow_sync(workflow_id, timeout)
        else:
            print(f"Unknown mode: {mode}")
            print(__doc__)
            sys.exit(1)
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main()

