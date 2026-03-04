import os
from redis import Redis
from rq import Worker, Queue, Connection

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
WORKER_NAME = os.environ.get("WORKER_NAME", "gpu")

listen = ["gpu"]

redis_conn = Redis.from_url(REDIS_URL)

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker(map(Queue, listen), name=WORKER_NAME)
        worker.work(with_scheduler=False)
