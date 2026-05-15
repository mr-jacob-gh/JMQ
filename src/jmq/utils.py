import time

from jmq import config, state


def write_to_log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(config.log_file_path, "a") as log_file:
        log_file.write(f"{timestamp} - {message}\n")


def print_stats():
    print('requests: ' + str(state.stats.get('requests')) + ' processed: ' + str(state.stats.get('processed')) +
          ' ignored: ' + str(state.stats.get('ignored')))
