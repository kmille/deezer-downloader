import time
import threading
import pytest
from deezer_downloader.threadpool_queue import ThreadpoolScheduler, QueuedTask, report_progress

def test_task_exception_handling():
    """
    Test that a task raising an exception is caught by the scheduler.
    The test verifies that the task's state becomes "failed"
    and the exception is recorded.
    """
    # Initialize the thread pool scheduler
    scheduler = ThreadpoolScheduler()
    # Define a dummy command that fails intentionally.
    @scheduler.register_command()
    def failing_task(x):
        raise ValueError("Intentional Failure")
    # Start the worker threads
    scheduler.run_workers(1)
    # Enqueue a task that will run the failing_task command.
    task = scheduler.enqueue_task("failing task", "failing_task", x=42)
    # Stop all workers (placing stop tokens in the queue)
    scheduler.stop_workers()
    # Check that the task failed and the exception is of type ValueError.
    assert task.state == "failed"
    assert isinstance(task.exception, ValueError)
def test_successful_task():
    """
    Test that a successful task:
    - Completes normally with state "mission accomplished"
    - Returns the expected result (sum of two numbers)
    - Updates progress values via the report_progress function.
    """
    scheduler = ThreadpoolScheduler()
    @scheduler.register_command()
    def successful_task(a, b):
        # Update progress to simulate work being done.
        report_progress(1, 10)
        time.sleep(0.1)
        report_progress(10, 10)
        return a + b
    scheduler.run_workers(1)
    task = scheduler.enqueue_task("addition task", "successful_task", a=3, b=4)
    scheduler.stop_workers()
    # Validate that the task completed as expected.
    assert task.state == "mission accomplished"
    assert task.result == 7
    assert task.progress == 10
    assert task.progress_maximum == 10
def test_enqueue_invalid_command_raises_key_error():
    """
    Test that enqueuing a task with an unregistered command raises a KeyError.
    This verifies that the scheduler correctly errors out when a command is missing.
    """
    scheduler = ThreadpoolScheduler()
    # Attempting to enqueue a task with a command that was never registered should
    # immediately raise a KeyError.
    with pytest.raises(KeyError):
        scheduler.enqueue_task("invalid task", "non_existent_command", foo=123)