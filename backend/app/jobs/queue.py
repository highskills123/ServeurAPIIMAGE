from redis import Redis
from rq import Queue
from ..config import settings

redis_client = Redis.from_url(settings.REDIS_URL)
redis_conn = redis_client  # backward-compat alias
q = Queue("gpu", connection=redis_client, default_timeout=600)
