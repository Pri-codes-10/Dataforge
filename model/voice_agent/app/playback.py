class MemoryPlayback:
    """Explicit test sink. No synthesis and no audible-latency claims."""
    provider = "test-memory (no audio)"

    def __init__(self):
        self.generation = 0
        self.queue = []
        self.submitted = []

    def stop(self, generation):
        self.generation = generation
        self.queue.clear()

    def submit(self, generation, text):
        if generation == self.generation:
            self.queue.append((generation, text))
            self.submitted.append((generation, text))

    def consume(self):
        while self.queue:
            generation, text = self.queue.pop(0)
            if generation == self.generation:
                return text
        return None
