import datetime
import random
import re
import time
from pathlib import Path

from jmq import config, state, zones
from jmq.utils import (
    write_to_log, write_priority_queue, write_ignore_list, sanitize_for_typing, looks_like_persona_break,
    clamp_reply_length,
)
from jmq.queue_manager import add_item_to_queue, already_in_queue
from jmq.llm_client import send_prompt_for, classify_spell_phrase, classify_zone_phrase
from jmq.zlem_persona import zlem

SPELL_MATCH_HIGH_CONFIDENCE = 90
ZONE_MATCH_CONFIDENCE = 90
COHERENCE_THRESHOLD = 30
SUGGESTION_TTL_SECONDS = 120

CONFIRMATION_PHRASES = {
    'y', 'ya', 'yah', 'ye', 'yea', 'yeah', 'yep', 'yes', 'yup', 'yessir',
    'yeh', 'confirm', 'correct', 'sure', 'aye', 'affirmative', 'please',
    'pls', 'do it', 'let\'s go',
}

CONFUSION_REPLIES = [
    "didn't catch that, try again in actual words.",
    "that mean something? cause it didn't land.",
    "not sure what you're going for there, chief.",
    "keyboard cat again? try that one more time.",
    "come again? that wasn't a sentence.",
    "gonna need actual words for that one.",
    "swing and a miss, try that again.",
    "that's not a word, and definitely not a request.",
    "run that by me again, slower this time.",
    "no clue what that was, try english.",
    "did your cat walk across the keyboard?",
    "that didn't parse. use your words.",
    "static on the line, say it again.",
    "huh? try that again with less gibberish.",
    "that's a whole lot of nothing, try again.",
    "missed whatever that was supposed to be.",
    "English motherfucker, do you speak it.",
    "you good? that made no sense.",
    "try that one again, actual words this time.",
    "nope, didn't mean anything to me.",
    "that's noise, not a request.",
    "words, chief. i need words.",
    "wut. try again.",
    "you dumb or something, try again.",
]

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


def extract_phrase(line):
    if 'tells you' not in line:
        return None

    # anchor on the tell marker so the timestamp prefix is not considered
    marker = "tells you, '"
    if marker not in line:
        return None
    start = line.index(marker) + len(marker)
    end = len(line) - 2
    return line[start:end].lower().strip('!?.,;@#$%^&*').strip()


def get_match(line):
    phrase = extract_phrase(line)
    if phrase is None:
        return None

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


def extract_command_target(line, command):
    """Return the argument following `command` in a tell (e.g. 'ignore playername'), or
    None if the tell isn't that command. Matching and the returned name are case-insensitive/
    lowercased, since extract_phrase lowercases the tell content.
    """
    phrase = extract_phrase(line)
    if phrase is None or not phrase.startswith(command + ' '):
        return None
    target = phrase[len(command):].strip()
    return target or None


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


def build_persona_context(name):
    if name in VIP_PLAYERS:
        familiarity = 'vip/priority'
    elif name in state.priority_queue:
        familiarity = 'vip/priority'
    else:
        familiarity = 'guild regular'
    return {'player_name': name, 'familiarity': familiarity}


PERSONA_BREAK_REPLIES = [
    "nice try, that's not happening.",
    "cute attempt, still not answering that.",
    "ask me for a buff instead, that one's not landing.",
    "swing and a miss, try something useful.",
]


def send_persona_reply(phrase, name, timestamp, q):
    def on_reply(reply, error):
        if not reply:
            return
        if looks_like_persona_break(reply):
            write_to_log(f'persona break filtered for {name}: {reply!r}')
            add_item_to_queue('tell', random.choice(PERSONA_BREAK_REPLIES), name, timestamp)
        else:
            add_item_to_queue('tell', clamp_reply_length(sanitize_for_typing(reply)), name, timestamp)

    system_prompt = zlem.render(context=build_persona_context(name))
    send_prompt_for(name, phrase, callback=on_reply, system_prompt=system_prompt)


def resolve_unrecognized_phrase(line, phrase, name, timestamp, q):
    def on_classified(spell, confidence, coherence, error):
        if error:
            send_persona_reply(phrase, name, timestamp, q)
            return

        if spell and confidence >= SPELL_MATCH_HIGH_CONFIDENCE:
            write_to_log(f'spell correction: treating "{phrase}" as "{spell}" ({confidence}% confident)')
            process_match(line, spell, timestamp, q)
        else:
            resolve_zone_phrase(phrase, name, timestamp, q, coherence)

    classify_spell_phrase(phrase, on_classified)


def resolve_zone_phrase(phrase, name, timestamp, q, coherence):
    def on_zone_classified(zone, confidence, error):
        if not error and zone and confidence > ZONE_MATCH_CONFIDENCE:
            port = zones.get_nearest_druid_port(zone, castable_spells=config.spells)
            if port:
                spell = port['spell']
                write_to_log(
                    f'zone correction: suggesting port "{spell}" toward "{zone}" for "{phrase}" '
                    f'({confidence}% confident)'
                )
                state.pending_suggestions[name] = {'spell': spell, 'timestamp': timestamp}
                if port['hops'] == 0:
                    suggestion = f"no spell match, but sounds like you want a port to {zone}? closest is '{spell}', want it?"
                else:
                    suggestion = (
                        f"no spell match, but sounds like you want to get to {zone}? closest port is "
                        f"'{spell}' to {port['port_zone']}, want it?"
                    )
                add_item_to_queue('tell', sanitize_for_typing(suggestion), name, timestamp)
                return

        if coherence < COHERENCE_THRESHOLD:
            write_to_log(f'phrase "{phrase}" deemed incoherent ({coherence}% coherence), sending canned reply')
            add_item_to_queue('tell', random.choice(CONFUSION_REPLIES), name, timestamp)
        else:
            send_persona_reply(phrase, name, timestamp, q)

    classify_zone_phrase(phrase, on_zone_classified)


def is_confirmation(phrase):
    return phrase in CONFIRMATION_PHRASES


def suggestion_is_fresh(suggestion, timestamp):
    suggested_at = suggestion.get('timestamp')
    if suggested_at is None or timestamp is None:
        return True
    return (timestamp - suggested_at).total_seconds() <= SUGGESTION_TTL_SECONDS


def resolve_confirmed_suggestion(line, phrase, name, timestamp, q):
    # Returns True if phrase was consumed as (or discarded as a stale) confirmation.
    suggestion = state.pending_suggestions.pop(name, None)
    if suggestion is None:
        return False

    if not is_confirmation(phrase):
        return False

    if not suggestion_is_fresh(suggestion, timestamp):
        write_to_log(f'suggestion for {name} expired, ignoring confirmation "{phrase}"')
        return False

    spell = suggestion['spell']
    write_to_log(f'{name} confirmed suggestion, queuing spell "{spell}"')
    process_match(line, spell, timestamp, q)
    return True


def handle_unmatched_line(line, timestamp, q):
    phrase = extract_phrase(line)
    name = extract_name(line)
    if (
        phrase is not None
        and name in state.roster.get('names')
        and (name).lower() not in state.ignore_list
    ):
        if not resolve_confirmed_suggestion(line, phrase, name, timestamp, q):
            resolve_unrecognized_phrase(line, phrase, name, timestamp, q)
            print('resolving unrecognized phrase: ' + phrase)


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
                if "group" in line.lower():
                    handle_unmatched_line(line, timestamp, q)
                else:
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
            elif extract_command_target(line, 'jwiestunignore') is not None:
                target = extract_command_target(line, 'jwiestunignore')
                if target in state.ignore_list:
                    state.ignore_list.remove(target)
                    write_ignore_list()
                    write_to_log(f'ignore list updated: removed {target}')
                    print('ignore list updated: ' + str(state.ignore_list))
            elif extract_command_target(line, 'jwiestignore') is not None:
                target = extract_command_target(line, 'jwiestignore')
                if target not in state.ignore_list:
                    state.ignore_list.append(target)
                    write_ignore_list()
                    write_to_log(f'ignore list updated: added {target}')
                    print('ignore list updated: ' + str(state.ignore_list))
            else:
                handle_unmatched_line(line, timestamp, q)