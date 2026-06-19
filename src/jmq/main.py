import datetime
import random
import threading
import time

from jmq import config, state
from jmq.actions import stand, sit, updateroster
from jmq.log_monitor import monitor_log
from jmq.queue_manager import process_queue
from jmq.spells import loaddefaultspells
from jmq.utils import print_stats, load_player_stats, load_priority_queue


def init():
    print('Script starting. Make EQ active window now!')
    load_player_stats()
    load_priority_queue()
    time.sleep(10)
    stand()
    sit()
    loaddefaultspells('luclin')


def keepalive():
    diff = datetime.datetime.now() - state.keep_alive.get('time')
    if state.q.qsize() == 0 and diff.seconds > (600 + random.randint(1, 10)):
        print('keep alive: ' + str(datetime.datetime.now()))
        state.q.put({'type': 'keep_alive', 'phrase': None, 'name': None})
        # stand()
        # sit()
        state.keep_alive['time'] = datetime.datetime.now()
        print_stats()


if __name__ == "__main__":
    init()

    # Start the log monitor thread
    log_monitor_thread = threading.Thread(target=monitor_log, args=(config.log_filepath, state.q))
    log_monitor_thread.daemon = True
    log_monitor_thread.start()

    # Start the queue processing thread
    queue_processor_thread = threading.Thread(target=process_queue, args=(state.q,))
    queue_processor_thread.daemon = True
    queue_processor_thread.start()

    updateroster()
    print('started...')

    try:
        while True:
            time.sleep(10)
            keepalive()
    except KeyboardInterrupt:
        print("Stopping...")
    except Exception as e:
        print(e)
