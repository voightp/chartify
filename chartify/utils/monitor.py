from esofile_reader.processor.monitor import DefaultMonitor


class GuiMonitor(DefaultMonitor):
    CHUNK_SIZE = 10000

    def __init__(self, path, id_, queue):
        super().__init__(path)
        self.queue = queue
        self.id = id_
        self.send_message(0, "Waiting")

    def done(self):
        self.send_message(100, "Done!")

    def totals_started(self):
        self.send_message(50, "Generating totals!")

    def set_chunk_size(self, n_lines):
        n_processing_steps = n_lines // self.CHUNK_SIZE

        # avoid having progress less then 10 steps
        if n_processing_steps < 10:
            self.max_progress = 10
        else:
            self.max_progress = n_processing_steps // self.PROGRESS_FRACTION

        super().set_chunk_size(n_lines)

    def update_progress(self, i=1):
        self.progress += i
        self.counter = 0
        self.send_message(99, self.progress)

    def report_progress(self, identifier, text):
        self.send_message(identifier, text)
        super().report_progress(identifier, text)

    def send_message(self, identifier, text):
        try:
            self.queue.put((self, identifier, text))
        except EOFError as e:
            print("Cannot send message!\n{}".format(e))
        except FileNotFoundError as e:
            print("Cannot find file!\n{}".format(e))
        except BrokenPipeError:
            print("App is being closed, cannot send message!")
