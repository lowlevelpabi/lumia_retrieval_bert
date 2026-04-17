import asyncio
import json
from typing import Dict, Any, AsyncGenerator

class TaskManager:
    def __init__(self):
        # session_id -> {"progress": int, "message": str, "status": str}
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def update_task(self, session_id: str, progress: int, message: str, status: str = "processing"):
        self.tasks[session_id] = {
            "progress": progress,
            "message": message,
            "status": status
        }
        print(f"[TaskManager] {session_id}: {progress}% - {message}")

    def get_task(self, session_id: str) -> Dict[str, Any]:
        return self.tasks.get(session_id, {"progress": 0, "message": "Waiting...", "status": "pending"})

    async def subscribe(self, session_id: str) -> AsyncGenerator[str, None]:
        """
        SSE Generator: Streams status updates for a specific session.
        Added padding and heartbeat to support Cloudflare/Proxies.
        """
        # 1. Send 2KB of padding to force Cloudflare/Proxies to flush the buffer
        yield f": {' ' * 2048}\n\n"
        
        last_progress = -1
        last_message = ""
        heartbeat_count = 0
        
        while True:
            task = self.get_task(session_id)
            curr_progress = task["progress"]
            curr_message = task["message"]
            
            # 2. Only send if something changed
            if curr_progress != last_progress or curr_message != last_message:
                yield f"data: {json.dumps(task)}\n\n"
                last_progress = curr_progress
                last_message = curr_message
            else:
                # 3. Heartbeat: Send a comment every ~15 seconds to keep connection alive
                heartbeat_count += 1
                if heartbeat_count >= 30: # 30 * 0.5s = 15s
                    yield ": heartbeat\n\n"
                    heartbeat_count = 0
            
            if task["status"] in ["completed", "failed"]:
                # Final push
                yield f"data: {json.dumps(task)}\n\n"
                break
                
            await asyncio.sleep(0.5)

    def remove_task(self, session_id: str):
        if session_id in self.tasks:
            del self.tasks[session_id]

task_manager = TaskManager()
