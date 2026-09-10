"""Generation fencing at LiveKit speech submission and interruption.

LiveKit owns final device/WebRTC buffering. This adapter logs submission and handle
completion, never mislabels them as the time a listener first heard audio.
"""
class LiveKitPlayback:
    provider = "Rime (LiveKit plugin)"

    def __init__(self, session, event_sink=None):
        self.session = session
        self.generation = 0
        self.handles = set()
        self.event_sink = event_sink or (lambda *args, **kwargs: None)

    def submit(self, generation, text):
        if generation != self.generation:
            self.event_sink("stale_playback_rejected", launched_gen=generation)
            return
        handle = self.session.say(text, allow_interruptions=True, add_to_chat_ctx=False)
        self.handles.add(handle)
        def done(completed):
            self.handles.discard(completed)
            self.event_sink("speech_handle_done", launched_gen=generation,
                            interrupted=completed.interrupted)
        handle.add_done_callback(done)

    def stop(self, generation):
        self.generation = generation
        for handle in tuple(self.handles):
            handle.interrupt()
        self.handles.clear()
        try:
            self.session.interrupt()
        except RuntimeError:
            self.event_sink("playback_session_not_running")
        self.event_sink("playback_stop_requested", new_generation=generation)
