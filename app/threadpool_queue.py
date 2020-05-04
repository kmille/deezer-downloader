import threading
import time
from queue import Queue

local_obj = threading.local()

class ThreadpoolScheduler:
    def __init__(self):
        print("creating Threadpool")
        self.task_queue = Queue()
        self.commands = {}
        self.worker_threads = []
        self.all_tasks = []
    
    def run_workers(self, num_workers):
        for i in range(num_workers):
            t = WorkerThread(i, self.task_queue)
            t.start()
            self.worker_threads.append(t)

    def enqueue_task(self, description, command, **kwargs):
        q = QueuedTask(description, command, self.commands[command], **kwargs)
        self.task_queue.put(q)
        self.all_tasks.append(q)
        return q

    def register_command(self):
        def decorator(fun):
            self.commands[fun.__name__] = fun
            return fun
        return decorator
    
    def stop_workers(self):
        for i in range(len(self.worker_threads)):
            self.task_queue.put(False)
        for worker in self.worker_threads:
            worker.join()
        print("All workers stopped")



class WorkerThread(threading.Thread):
    def __init__(self, index, task_queue):
        super().__init__()
        self.index = index
        self.task_queue = task_queue

    def run(self):
        while True:
            print("worker "+str(self.index)+" waiting for task")
            task = self.task_queue.get(block=True)
            if task == False:
                print("worker "+str(self.index)+" exiting")
                return
            print("worker "+str(self.index)+": setting task "+str(task)+ " to active")
            task.state = "active"
            self.ts_started = time.time()
            task.worker_index = self.index
            local_obj.current_task = task
            try:
                task.result = task.exec()
                task.state = "finished"
            except Exception as ex:
                task.state = "failed"
                task.exception = ex
            self.ts_finished = time.time()


class QueuedTask:
    def __init__(self, description, fn_name, fn, **kwargs):
        self.description = description
        self.fn_name = fn_name
        self.fn = fn
        self.kwargs = kwargs
        self.state = "waiting"
        self.exception = None
        self.result = None
        self.progress = 0
        self.progress_maximum = 0
        self.ts_queued = time.time()
        self.ts_started = 0
        self.ts_finished = 0

    def exec(self):
        return self.fn(**self.kwargs)


def self_task():
    return local_obj.current_task

def report_progress(value,maximum):
    local_obj.current_task.progress = value
    local_obj.current_task.progress_maximum = maximum

