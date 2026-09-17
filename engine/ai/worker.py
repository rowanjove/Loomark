import asyncio
import logging
from typing import Optional
from engine.db.repository import Repository
from engine.ai.client import AIProviderClient
from engine.ai.cache import AICache

from engine.db.session import get_db

logger = logging.getLogger(__name__)

class AIQueueWorker:
    """
    Independent asynchronous background AI worker (PRD Section 40 & 44).
    Processes summary, tag generation and classification tasks without
    blocking crawler execution.
    """
    def __init__(self, repo: Optional[Repository] = None, ai_client: Optional[AIProviderClient] = None):
        self.repo = repo
        self.ai_client = ai_client
        self.queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self.cache = AICache(repo)

    def start(self):
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._process_queue())

    def stop(self):
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()

    def enqueue_document(self, document_id: str, project_id: str,
                         task_type: str = "article_summary_v1",
                         model: Optional[str] = None):
        self.queue.put_nowait({
            "document_id": document_id,
            "project_id": project_id,
            "task_type": task_type,
            "model": model
        })

    async def _process_queue(self):
        while self._running:
            try:
                task_item = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                doc_id = task_item["document_id"]
                project_id = task_item["project_id"]
                task_type = task_item["task_type"]
                model = task_item.get("model")

                if self.ai_client is None:
                    continue

                with get_db() as conn:
                    repo = Repository(conn)
                    doc = repo.get_document(doc_id)

                if not doc:
                    continue

                res = await self.ai_client.execute_task(
                    task_type=task_type,
                    content=doc["text"] or doc["markdown"],
                    title=doc["title"],
                    model=model,
                    cache=self.cache,
                    content_hash=doc["content_hash"]
                )

                if "error" not in res:
                    with get_db() as conn:
                        repo = Repository(conn)
                        repo.create_ai_artifact(
                            document_id=doc_id,
                            project_id=project_id,
                            artifact_type=task_type,
                            model=res["model"],
                            provider="openai_compatible",
                            prompt_version="v1.0",
                            result_json=res["result"],
                            input_tokens=res.get("input_tokens", 0),
                            output_tokens=res.get("output_tokens", 0),
                            cost=res.get("cost", 0.0)
                        )
            except asyncio.CancelledError:
                self.queue.task_done()
                break
            except Exception as e:
                logger.error(f"Error in AI worker processing: {e}")
                await asyncio.sleep(0.5)
            finally:
                # Guarantee task_done is called for every successfully received item
                try:
                    self.queue.task_done()
                except ValueError:
                    pass
