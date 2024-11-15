import time
from pyinstrument import Profiler

from common import logger
from common.config_class.profiler import ProfilerConfig

profiler_config: None | ProfilerConfig = None


def init_profiler(config: ProfilerConfig):
    global profiler_config
    profiler_config = config


def __wrapper_profiler(func, *args, **kwargs):
    global profiler_config
    if profiler_config is None:
        return func(*args, **kwargs)

    profiler = Profiler()
    profiler.start()
    result = func(*args, **kwargs)
    profiler.stop()

    if profiler_config.activated:
        if profiler_config.output_file is not None:
            with open(profiler_config.output_file, "w") as f:
                f.write(profiler.output_html())
        if profiler_config.profile_function:
            logger.log_profiler(profiler)

    return result


def __wrapper_timeit(func, *args, **kwargs):
    global profiler_config
    if profiler_config is None:
        return func(*args, **kwargs)

    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()

    if profiler_config.activated:
        if profiler_config.output_file is not None:
            with open(profiler_config.output_file, "a") as f:
                f.write(f"{func.__name__} took {end_time - start_time:.4f} seconds\n")
        if profiler_config.time_function:
            logger.debug(
                f"{func.__name__} took {end_time - start_time:.4f} seconds or {1000 * (end_time - start_time):.4f} ms"
            )

    return result


def profile_function(func):
    def wrapper(*args, **kwargs):
        return __wrapper_profiler(func, *args, **kwargs)

    return wrapper


def timeit(func):
    def wrapper(*args, **kwargs):
        return __wrapper_timeit(func, *args, **kwargs)

    return wrapper
