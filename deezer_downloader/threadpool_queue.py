import threading
import time
from queue import Queue

local_obj = threading.local()


class ThreadpoolScheduler:

    def __init__(self):
        self.task_queue = Queue() # threadsafe queue where we put/get QueuedTask objects
        self.worker_threads = [] # list of WorkerThread objects

        # self.commands: {'function_name': function_pointer_to_the_function}
        # {'download_deezer_song_and_queue': <function download_deezer_song_and_queue at 0x7ff81d739280>}
        self.commands = {}

        # list of all QueuedTask objects we processed during runtime (used by /queue)
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
        # print("All workers stopped")


class WorkerThread(threading.Thread):

    def __init__(self, index, task_queue):
        super().__init__(daemon=True)
        self.index = index # just an id per Worker
        self.task_queue = task_queue # shared between all WorkerThreads

    def run(self):
        while True:
            # print(f"Worker {self.index} is waiting for a task")
            task = self.task_queue.get(block=True)
            if not task:
                # print(f"Worker {self.index} is exiting")
                return
            # print(f"Worker {self.index} is now working on task: {task.kwargs}")
            task.state = "active"
            self.ts_started = time.time()
            task.worker_index = self.index
            local_obj.current_task = task
            try:
                task.result = task.exec()
                task.state = "mission accomplished"
            except Exception as ex:
                print(f"Task {task.fn_name} failed with parameters '{task.kwargs}'\nReason: {ex}")
                task.state = "failed"
                task.exception = ex
            self.ts_finished = time.time()
            # print(f"worker {self.index} is done with task: {task.kwargs} (state={task.state})")


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


def report_progress(value, maximum):
    local_obj.current_task.progress = value
    local_obj.current_task.progress_maximum = maximum
