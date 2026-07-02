import datetime
import importlib
import random
import threading
import time

from jmq import config, state
from jmq.actions import stand, sit, updateroster
from jmq.log_monitor import monitor_log
from jmq.queue_manager import process_queue
from jmq.spells import loaddefaultspells
from jmq.utils import (
    print_stats, load_player_stats, load_priority_queue, load_conversation_history, load_ignore_list,
)

# Map a class string to the module holding that class's spell config.
CLASS_CONFIGS = {
    'druid': 'jmq.druid_config',
    'cleric': 'jmq.cleric_config',
    'enchanter': 'jmq.enchanter_config',
}


def load_class_config(eq_class):
    if eq_class not in CLASS_CONFIGS:
        raise ValueError(
            f"Unknown class '{eq_class}'. Valid classes: {', '.join(CLASS_CONFIGS)}"
        )
    class_config = importlib.import_module(CLASS_CONFIGS[eq_class])
    config.spells = class_config.spells
    config.spell_ids = class_config.spell_ids
    config.master_phrase_map = class_config.master_phrase_map
    config.group_spells = class_config.group_spells
    config.default_spells = class_config.default_spells


def init(eq_class):
    print(f'Script starting as {eq_class}. Make EQ active window now!')
    load_class_config(eq_class)
    load_player_stats()
    load_priority_queue()
    load_conversation_history()
    load_ignore_list()
    time.sleep(10)
    stand()
    sit()
    loaddefaultspells('velious')


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
    init('druid')

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
