from redis import Redis
from rq import Queue
from ..config import settings

redis_conn = Redis.from_url(settings.REDIS_URL)
q = Queue("gpu", connection=redis_conn, default_timeout=600)
