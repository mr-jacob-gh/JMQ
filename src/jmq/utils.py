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


_PERSONA_BREAK_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        r"\bas an ai\b",
        r"\bi'?m an ai\b",
        r"\bi am an ai\b",
        r"\blanguage model\b",
        r"\bi'?m a bot\b",
        r"\bi am a bot\b",
        r"\bas a bot\b",
        r"\bi'?m a chatbot\b",
        r"\bi'?m an assistant\b",
        r"\bas an assistant\b",
        r"\bvirtual assistant\b",
        r"\bsystem prompt\b",
        r"\bmy instructions\b",
        r"\bopenai\b",
        r"\banthropic\b",
        r"\bi'?m just a program\b",
        r"\bi'?m a script\b",
    ]
]


def looks_like_persona_break(text):
    """True if the text contains a known identity-leak/persona-break signature
    (e.g. "as an AI", "language model", "system prompt"), used as a deterministic
    backstop against prompt injection before a reply is sent to a player.
    """
    return any(pattern.search(text) for pattern in _PERSONA_BREAK_PATTERNS)


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


def load_ignore_list():
    if os.path.exists(config.ignore_list_file_path):
        with open(config.ignore_list_file_path, 'r') as f:
            loaded = json.load(f)
            state.ignore_list.clear()
            state.ignore_list.extend(loaded)
    else:
        write_ignore_list()


def write_ignore_list():
    with open(config.ignore_list_file_path, 'w') as f:
        json.dump(state.ignore_list, f, indent=2)


def load_conversation_history():
    if os.path.exists(config.conversation_history_file_path):
        with open(config.conversation_history_file_path, 'r') as f:
            state.conversation_history.update(json.load(f))


def write_conversation_history():
    with open(config.conversation_history_file_path, 'w') as f:
        json.dump(state.conversation_history, f, indent=2)
