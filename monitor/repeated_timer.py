from threading import Timer


class RepeatedTimer(object):
    """Run a job at a repeated time

    From: https://stackoverflow.com/questions/2398661/schedule-a-repeating-event-in-python-3
    """

    def __init__(self, interval, job, *args, **kwargs):
        self._timer = None
        self.job = job  # The function that will be called
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self.is_running = False  # Flag to avoid starting several time the same scheduler
        self.start()

    def _run(self):
        self.is_running = False
        # Restart the timer before calling the function job to respect the timing
        self.start()
        self.job(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            # Will call _run in {self.interval} seconds
            self._timer = Timer(self.interval, self._run)
            # Start the timer (not the scheduler/repeated timer)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False
