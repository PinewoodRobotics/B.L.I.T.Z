from threading import Thread


class ModuleThread(Thread):
    is_running: bool = False

    def stop(self):
        self.is_running = False
