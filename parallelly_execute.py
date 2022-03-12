from multiprocessing.pool import ThreadPool
from queue import Queue
from typing import Callable


def parallelly_execute(resources: list, threads: int, worker: Callable[[int, int, any], None]) -> int:
    """worker<index, total, resource>
    返回值：成功执行的任务数量
    """
    # 准备任务
    task_pool = Queue(1000000000)
    thread_pool = ThreadPool(threads)

    for resource in resources:
        task_pool.put(resource)
    
    total = task_pool.qsize()
    finishes = -1

    def task_worker():
        nonlocal finishes
        while not task_pool.empty():
            resource = task_pool.get(timeout=1)
            finishes += 1
            worker(finishes, total, resource)
    
    ex = None

    def onError(e):
        nonlocal ex
        thread_pool.terminate()
        ex = e

    for i in range(0, threads):
        thread_pool.apply_async(task_worker, error_callback=onError)
    
    thread_pool.close()
    thread_pool.join()

    if ex is not None:
        raise ex
    
    return finishes