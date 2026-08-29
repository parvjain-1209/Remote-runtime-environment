"""
Redis Queue Client for Submissions Stream.
"""

import logging
from typing import Optional
import redis

from app.config import settings

logger = logging.getLogger(__name__)


class QueueClient:
    """
    Redis Streams Queue Client for enqueuing submission job IDs.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self.stream_name = settings.redis_stream_name
        self.group_name = settings.redis_consumer_group
        self._redis_client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        """Lazy-loaded Redis client instance."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis_client

    def ensure_consumer_group(self) -> None:
        """Ensures the Redis Stream consumer group exists."""
        try:
            self.client.xgroup_create(
                name=self.stream_name,
                groupname=self.group_name,
                id="$",
                mkstream=True,
            )
        except redis.exceptions.ResponseError as err:
            if "BUSYGROUP" in str(err):
                pass  # Consumer group already exists
            else:
                raise

    def enqueue_submission(self, submission_id: str) -> str:
        """
        Enqueues submission ID to Redis Stream with approximate trimming (MAXLEN ~ 10000).

        Args:
            submission_id: Unique UUID of created submission.

        Returns:
            Redis Stream message ID.
        """
        self.ensure_consumer_group()
        msg_id = self.client.xadd(
            name=self.stream_name,
            fields={"submission_id": submission_id},
            maxlen=10000,
            approximate=True,
        )
        logger.info(f"Enqueued submission '{submission_id}' to stream '{self.stream_name}' (msg_id={msg_id})")
        return str(msg_id)

    def ping(self) -> bool:
        """Pings Redis server to verify availability."""
        try:
            return bool(self.client.ping())
        except Exception:
            return False


# Shared global queue client instance
queue_client = QueueClient()
