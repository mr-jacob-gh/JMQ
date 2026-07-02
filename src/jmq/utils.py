import json
import os
import re
import time

from jmq import config, state


_TYPOGRAPHIC_REPLACEMENTS = {
    '‘': "'", '’': "'",   # ‘ ’
    '“': '"', '”': '"',   # “ ”
    '–': '-', '—': '-',   # – —
    '…': '...',                # …
}


def sanitize_for_typing(text):
    for src, dst in _TYPOGRAPHIC_REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def write_to_log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(config.log_file_path, "a") as log_file:
        log_file.write(f"{timestamp} - {message}\n")


def print_stats():
    print('requests: ' + str(state.stats.get('requests')) + ' processed: ' + str(state.stats.get('processed')) +
          ' ignored: ' + str(state.stats.get('ignored')))


def load_player_stats():
    if os.path.exists(config.player_stats_file_path):
        with open(config.player_stats_file_path, 'r') as f:
            state.player_stats.update(json.load(f))


def write_player_stats():
    with open(config.player_stats_file_path, 'w') as f:
        json.dump(state.player_stats, f, indent=2)


def load_priority_queue():
    if os.path.exists(config.priority_queue_file_path):
        with open(config.priority_queue_file_path, 'r') as f:
            loaded = json.load(f)
            state.priority_queue.clear()
            state.priority_queue.extend(loaded)
    else:
        write_priority_queue()


def write_priority_queue():
    with open(config.priority_queue_file_path, 'w') as f:
        json.dump(state.priority_queue, f, indent=2)


def load_conversation_history():
    if os.path.exists(config.conversation_history_file_path):
        with open(config.conversation_history_file_path, 'r') as f:
            state.conversation_history.update(json.load(f))


def write_conversation_history():
    with open(config.conversation_history_file_path, 'w') as f:
        json.dump(state.conversation_history, f, indent=2)
