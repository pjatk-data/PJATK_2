import time


class Stopwatch:
    """
    A class representing a stopwatch for measuring elapsed time.

    Attributes:
        elapsed (float): The elapsed time in seconds.
        is_running (bool): A flag indicating whether the stopwatch is running
    """

    def __init__(self):
        """
        Initialize a new instance of the Stopwatch class.
        """
        self.elapsed = 0
        self.is_running = False
        self.start_time = 0

    def __enter__(self):
        """
        Enters a context block and starts the stopwatch.

        Returns:
            Stopwatch: The stopwatch instance.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exits the context block and stops the stopwatch.
        """
        self.stop()

    def reset(self):
        """
        Resets the stopwatch by setting the elapsed time to zero and stopping it
        """
        self.elapsed = 0
        self.is_running = False

    def start(self):
        """
        Starts the stopwatch by setting the start time and setting the 'is_running' flag to True.
        """
        if self.is_running:
            return

        self.is_running = True
        self.start_time = time.perf_counter()

    def stop(self):
        """
        Stops the stopwatch by calculating the elapsed time and setting the 'is_running' flag to False.
        """
        if not self.is_running:
            return

        self.is_running = False
        self.elapsed = time.perf_counter() - self.start_time

    def get_current_elapsed(self):
        """
        Gets the current elapsed time without stopping the stopwatch.

        Returns:
            float: The current elapsed time in seconds.
        """
        if not self.is_running:
            return self.elapsed

        return time.perf_counter() - self.start_time

    def elapsed_ms(self):
        """
        Gets the elapsed time in milliseconds.

        Returns:
            float: The elapsed time in milliseconds.
        """
        if self.is_running:
            current_elapsed = time.perf_counter() - self.start_time
            return current_elapsed * 1000
        return self.elapsed * 1000
