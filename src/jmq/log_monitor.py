import datetime
import re
import time
from pathlib import Path

from jmq import config, state
from jmq.utils import write_to_log, write_priority_queue
from jmq.queue_manager import add_item_to_queue, already_in_queue

VIP_PLAYERS = [
    'Vicious', 'Melz', 'Porco', 'Avenue', 'Lachmar', 'Savory', 'Straxus',
    'Atiesh', 'Avenuetwo', 'Colonclysm', 'Hotfudge', 'Lachdawg', 'Lachdogg',
    'Mini', 'Vicc', 'Viccleric', 'Vicclrone', 'Vicdoze', 'Vicmage', 'Vicrog',
    'Vicwar', 'Vicwiz', 'Vindicus', 'Yani', 'Bloodthirst',
]


def tail(f):
    f.seek(0, 2)  # Go to the end of the file
    while True:
        try:
            line = f.readline()
            if not line:
                time.sleep(0.1)  # Sleep briefly before trying again
                continue
            yield line
        except Exception as e:
            print("failed to read line!")
            time.sleep(0.1)  # Sleep briefly before trying again
            continue


def extract_guild_roster(filename):
    names = []
    with open(filename, 'r') as file:
        for line in file:
            name = line.strip().split()[0]
            names.append(name)

    Path(filename).unlink()
    print(names)
    return names


def extract_timestamp(line):
    match = re.search(r'\[(\w+ \w+ \d+ \d+:\d+:\d+ \d+)]', line)
    if match:
        return datetime.datetime.strptime(match.group(1), '%a %b %d %H:%M:%S %Y')
    return None


def extract_name(log_line):
    match = re.search(r'\[\w+ \w+ \d+ \d+:\d+:\d+ \d+] (\w+) tells you,', log_line)
    if match:
        return match.group(1)
    return None


def get_match(line):
    if 'tells you' not in line:
        return None

    # anchor on the tell marker so the timestamp prefix is not considered
    marker = "tells you, '"
    if marker not in line:
        return None
    start = line.index(marker) + len(marker)
    end = len(line) - 2
    phrase = line[start:end].lower().strip('!?.,;@#$%^&*').strip()
    if phrase in config.master_phrase_map.keys():
        return config.master_phrase_map.get(phrase)
    else:  # compare each word in phrase to spell list
        split_phrase = phrase.split(' ')
        for word in split_phrase:
            if word in config.master_phrase_map.keys():
                return config.master_phrase_map.get(word)

        for i in range(len(split_phrase) - 1):
            two_word_combo = split_phrase[i] + ' ' + split_phrase[i + 1]
            if two_word_combo in config.master_phrase_map.keys():
                return config.master_phrase_map.get(two_word_combo)

    return None


def get_failure_match(line):
    for failure in config.failure_strings:
        if failure in line:
            return failure
    return None


def process_match(line, match, timestamp, q):
    write_to_log('match found: ' + line)
    state.stats['requests'] = state.stats.get('requests') + 1
    name = extract_name(line)
    if name in state.roster.get('names') and not already_in_queue(match, name):  # only for guild members.
        if (('vip' in line.lower() and name in VIP_PLAYERS) or name in state.priority_queue) and q.qsize() > 0:
            old_q = []
            while not q.empty():
                task = q.get_nowait()
                old_q.append(task)
                q.task_done()

            add_item_to_queue('spell', match, name, timestamp)
            for item in old_q:
                q.put(item)

        else:
            if 'vip' in line.lower() and name not in VIP_PLAYERS:
                add_item_to_queue('vipmessage', match, name, timestamp)
            add_item_to_queue('spell', match, name, timestamp)
    else:
        print('ignored message: ' + line)
        state.stats['ignored'] = state.stats.get('ignored') + 1


def monitor_log(filepath, q):
    block_roster = False
    with open(filepath, 'r', encoding="utf-8", errors="replace") as f:
        log_lines = tail(f)
        for line in log_lines:
            timestamp = extract_timestamp(line)
            match = get_match(line)
            failure = get_failure_match(line)
            if failure is not None:
                print(failure)
                state.failure_events.append({'timestamp': timestamp, 'failure': failure, 'line': line})
            if match is not None:
                process_match(line, match, timestamp, q)
            elif 'has joined your guild' in line or 'no longer a member of your guild' in line:
                q.put({'type': 'updateroster', 'phrase': None, 'name': None})
            elif 'updateroster' in line and block_roster is False:
                q.put({'type': 'updateroster', 'phrase': None, 'name': None})
            elif 'Outputfile Complete' in line:
                filename = line.split(': ')[1].strip('\n')
                print('roster filename: ' + filename)
                state.roster['names'] = extract_guild_roster(config.roster_filepath + filename)
            elif 'jwiestadd' in line:
                name = line.split('jwiestadd')[1].strip('\n\'').strip()
                print(name)
                state.roster['names'].append(name)
            elif 'jwiestremove' in line:
                name = line.split('jwiestremove')[1].strip('\n\'').strip()
                print(name)
                state.roster['names'].remove(name)
            elif 'blockroster' in line:
                block_roster = not block_roster
                state.roster['names'] = ['melz']
            elif 'status' in line:
                q.put({'type': 'status', 'phrase': '', 'name': extract_name(line)})
            elif 'my stats' in line:
                q.put({'type': 'stats', 'phrase': '', 'name': extract_name(line)})
            elif 'jwiesttotalstats' in line:
                q.put({'type': 'totalstats', 'phrase': '', 'name': extract_name(line)})
            elif 'food' in line.lower() and 'tells you' in line.lower():
                q.put({'type': 'food', 'phrase': '', 'name': extract_name(line)})
            elif 'drink' in line.lower() and 'tells you' in line.lower():
                q.put({'type': 'drink', 'phrase': '', 'name': extract_name(line)})
            elif 'jwiestpqadd' in line:
                name = line.split('jwiestpqadd')[1].strip('\n\'').strip()
                if name and name not in state.priority_queue:
                    state.priority_queue.append(name)
                    write_priority_queue()
                    print('priority queue updated: ' + str(state.priority_queue))
            elif 'jwiestpqremove' in line:
                name = line.split('jwiestpqremove')[1].strip('\n\'').strip()
                if name and name in state.priority_queue:
                    state.priority_queue.remove(name)
                    write_priority_queue()
                    print('priority queue updated: ' + str(state.priority_queue))