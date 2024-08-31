import queue
import threading
from pathlib import Path

import pyKey
import time
import re
import datetime
import random


def extract_guild_roster(filename):
    names = []
    with open(filename, 'r') as file:
        for line in file:
            name = line.strip().split()[0]
            names.append(name)

    Path(filename).unlink()
    print(names)
    return names


def write_to_log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file_path, "a") as log_file:
        log_file.write(f"{timestamp} - {message}\n")


def tail(f):
    f.seek(0, 2)  # Go to the end of the file
    while True:
        line = f.readline()
        if not line:
            time.sleep(0.1)  # Sleep briefly before trying again
            continue
        yield line


def extract_name(log_line):
    match = re.search(r'\[\w+ \w+ \d+ \d+:\d+:\d+ \d+] (\w+) tells you,', log_line)
    if match:
        return match.group(1)
    return None


def monitor_log(filepath, q):
    with open(filepath, 'r') as f:
        log_lines = tail(f)
        for line in log_lines:
            match = get_match(line)
            if match is not None:
                write_to_log('match found: ' + line)
                stats['requests'] = stats.get('requests') + 1
                name = extract_name(line)
                if name in roster.get('names') and not already_in_queue(match, name):  # only for guild members.
                    if 'vip' in line.lower() and q.qsize() > 0:
                        old_q = []
                        while not q.empty():
                            task = q.get_nowait()
                            old_q.append(task)
                            q.task_done()

                        add_item_to_queue('spell', match, name)
                        for item in old_q:
                            q.put(item)

                    else:
                        add_item_to_queue('spell', match, name)
                else:
                    print('ignored message: ' + line)
                    stats['ignored'] = stats.get('ignored') + 1
            elif 'has joined your guild' in line or 'no longer a member of your guild' in line:
                q.put({'type': 'updateroster', 'phrase': None, 'name': None})
            elif 'updateroster' in line:
                q.put({'type': 'updateroster', 'phrase': None, 'name': None})
            elif 'Outputfile Complete' in line:
                filename = line.split(': ')[1].strip('\n')
                print('roster filename: ' + filename)
                roster['names'] = extract_guild_roster(roster_filepath + filename)
            elif 'jwiestadd' in line:
                name = line.split('jwiestadd')[1].strip('\n\'').strip()
                print(name)
                roster['names'].append(name)
            elif 'status' in line:
                q.put({'type': 'status', 'phrase': '', 'name': extract_name(line)})


def get_match(line):
    if 'tells you' not in line:
        return None

    # compare entire phrase to spell list
    start = line.index('\'') + 1
    end = len(line) - 2
    phrase = line[start:end].lower().strip('!?.,;@#$%^&*').strip()
    if phrase in master_phrase_map.keys():
        return master_phrase_map.get(phrase)
    else:  # compare each word in phrase to spell list
        split_phrase = phrase.split(' ')
        for word in split_phrase:
            if word in master_phrase_map.keys():
                return master_phrase_map.get(word)

        for i in range(len(split_phrase)-1):
            two_word_combo = split_phrase[i]+' '+split_phrase[i+1]
            if two_word_combo in master_phrase_map.keys():
                return master_phrase_map.get(two_word_combo)

    return None


def process_queue(q):
    req_type = None
    phrase = None
    name = None
    while True:
        try:
            standsit = True
            task = q.get()  # This blocks until a new item is available in the queue
            req_type = task.get('type')
            phrase = task.get('phrase')
            name = task.get('name')
            write_to_log('processing queue task: ' + str(req_type) + ', ' + str(phrase) + ', ' + str(name))

            if req_type == 'spell':
                process_spell_request(name, phrase)
            elif req_type == 'status':
                send_status(name)
                standsit = False
            elif req_type == 'keep_alive':
                press('LSHIFT')
                standsit = False
            elif req_type == 'updateroster':
                updateroster()
                standsit = False

        finally:
            write_to_log('removing queue task: ' + str(req_type) + ', ' + str(phrase) + ', ' + str(name))
            q.task_done()
            if {'type': req_type, 'phrase': phrase, 'name': name} in q_list.get('items'):
                q_list.get('items').remove({'type': req_type, 'phrase': phrase, 'name': name})

        # q.task_done()
        if q.qsize() == 0 and standsit:
            stand()
            sit()


def add_item_to_queue(_type, phrase, name):
    match = False
    for item in q_list.get('items'):
        if item.get('type') == _type and item.get('phrase') == phrase and item.get('name') == name:
            match = True
            break

    if not match:
        q.put({'type': _type, 'phrase': phrase, 'name': name})
        q_list['items'].append({'type': _type, 'phrase': phrase, 'name': name})


def already_in_queue(phrase, name):
    if {'type': 'spell', 'phrase': phrase, 'name': name} in q_list.get('items'):
        return True
    return False


def print_stats():
    print('requests: ' + str(stats.get('requests')) + ' processed: ' + str(stats.get('processed')) +
          ' ignored: ' + str(stats.get('ignored')))


def press(key):
    pyKey.press(key)
    time.sleep(0.1)


def process_group_spell(name, phrase):
    press('ENTER')
    pyKey.sendSequence('/invite')
    press('SPACEBAR')
    pyKey.pressKey('LSHIFT')
    pyKey.sendSequence(name[0].lower())
    pyKey.releaseKey('LSHIFT')
    pyKey.sendSequence(name[1:])
    press('ENTER')
    # press('ENTER')
    # pyKey.sendSequence('/tt accept invite casting in 5sec')
    # press('ENTER')
    send_tell_to_current_target('Accept group invite - casting in 5 seconds!')
    time.sleep(6)
    castspell(phrase)
    press('ENTER')
    pyKey.sendSequence('/disband')
    press('ENTER')
    press('ENTER')
    pyKey.sendSequence('/raiddisband')
    press('ENTER')


def notify_queue_position(name, phrase, pos):
    send_tell(name, phrase + ' in queue at pos: ' + str(pos))


def process_spell_request(name, phrase):
    print('casting ' + phrase + ' on ' + name)
    # clear target
    press('ESC')
    # activate chat window
    press('ENTER')
    # target the player
    pyKey.sendSequence('/tar')
    press('SPACEBAR')
    pyKey.pressKey('LSHIFT')
    pyKey.sendSequence(name[0].lower())
    pyKey.releaseKey('LSHIFT')
    pyKey.sendSequence(name[1:])
    press('ENTER')

    if phrase in group_spells:
        process_group_spell(name, phrase)
    else:
        # press('ENTER')
        # pyKey.sendSequence('/tt ' + phrase + ' inc')
        # press('ENTER')
        # cast the spell
        time.sleep(0.2)
        castspell(phrase)

    keep_alive['time'] = datetime.datetime.now()
    stats['processed'] = stats.get('processed') + 1


def send_status(name):
    if name in roster.get('names'):
        send_tell(name, 'online')


def send_tell(name, msg):
    # activate chat window
    press('ENTER')
    pyKey.sendSequence('/tell')
    press('SPACEBAR')
    pyKey.pressKey('LSHIFT')
    pyKey.sendSequence(name[0].lower())
    pyKey.releaseKey('LSHIFT')
    pyKey.sendSequence(name)
    press('SPACEBAR')
    pyKey.sendSequence(msg)
    press('ENTER')
    keep_alive['time'] = datetime.datetime.now()


def send_tell_to_current_target(msg):
    # activate chat window
    press('ENTER')
    pyKey.sendSequence('/tt')
    press('SPACEBAR')
    for token in msg.split(' '):
        pyKey.sendSequence(token)
        press('SPACEBAR')
    press('ENTER')
    keep_alive['time'] = datetime.datetime.now()


def sit():
    press('ENTER')
    pyKey.sendSequence('/sit')
    press('ENTER')


def stand():
    press('ENTER')
    pyKey.sendSequence('/stand')
    press('ENTER')


def clearspell(slot):
    press('ENTER')
    pyKey.sendSequence('/memspellslot')
    press('SPACEBAR')
    pyKey.sendSequence(str(slot))
    press('SPACEBAR')
    pyKey.sendSequence('0')
    press('ENTER')


def memspell(spell, slot):
    # print('spell in slot: '+str(slot)+' is '+str(memorized_spells.get(slot)))
    #  clearspell(slot)
    # can't have anything on cursor when trying to mem spells, stop mod rods from breaking script
    press('ENTER')
    pyKey.sendSequence('/autoinv')
    press('ENTER')
    # mem the spell
    press('ENTER')
    pyKey.sendSequence('/memspellslot')
    press('SPACEBAR')
    pyKey.sendSequence(str(slot))
    press('SPACEBAR')
    pyKey.sendSequence(spell_ids.get(spell))
    press('ENTER')
    # accounts for spellbar cooldown timer

    time.sleep(2.8)
    memorized_spells[slot] = spell
    last_cast_time[spell] = datetime.datetime.now()
    # print(spell + ' memorized')


def castspell(spell):
    slot = spells.get(spell).get('slot')
    if memorized_spells.get(slot) != spell:
        send_tell_to_current_target('memorizing spell - one moment')
        memspell(spell, spells.get(spell).get('slot'))

    if last_cast_time.get(spell) is not None:
        diff = datetime.datetime.now() - last_cast_time.get(spell)
        if diff.seconds < spells.get(spell).get('recasttime'):
            time.sleep((spells.get(spell).get('recasttime') - diff.seconds) + 2.0)
            # print('pausing for recast time')

    print('now casting: ' + spell)
    key = spell_slot_keys.get(spells.get(spell).get('slot'))
    tell_spell_inc(spell)
    pyKey.sendSequence('/cast')
    press('SPACEBAR')
    pyKey.sendSequence(str(spells.get(spell).get('slot')))
    press('ENTER')
    cast_time = spells.get(spell).get('casttime')
    focus_reduction = cast_time * 0.15
    time.sleep(cast_time + 2.5)
    last_cast_time[spell] = datetime.datetime.now()


def tell_spell_inc(spell):
    press('ENTER')
    pyKey.sendSequence('/tt')
    press('SPACEBAR')
    pyKey.sendSequence(spell)
    press('SPACEBAR')
    pyKey.sendSequence('inc')
    press('ENTER')


def updateroster():
    press('ENTER')
    pyKey.sendSequence('/outputfile')
    press('SPACEBAR')
    pyKey.sendSequence('guild')
    press('SPACEBAR')
    pyKey.sendSequence('gr')
    print('pause')
    press('ENTER')


def loaddefaultspells(xpac):
    if xpac == 'kunark':
        memspell('heal', spells.get('heal').get('slot'))
        memspell('sow', spells.get('sow').get('slot'))
        memspell('natureskin', spells.get('natureskin').get('slot'))
        memspell('feerrott', spells.get('feerrott').get('slot'))
        memspell('bb', spells.get('bb').get('slot'))
        memspell('sf', spells.get('sf').get('slot'))
        memspell('ej', spells.get('ej').get('slot'))
        memspell('toxx', spells.get('toxx').get('slot'))
    elif xpac == 'velious':
        memspell('gopt', spells.get('gopt').get('slot'))
        memspell('gob', spells.get('gob').get('slot'))
        memspell('vog', spells.get('vog').get('slot'))
        memspell('grm', spells.get('grm').get('slot'))
    elif xpac == 'luclin':
        memspell('heal', spells.get('heal').get('slot'))
        memspell('soe', spells.get('soe').get('slot'))
        memspell('potc', spells.get('potc').get('slot'))
        memspell('dawn', spells.get('dawn').get('slot'))
        memspell('grim', spells.get('grim').get('slot'))
        memspell('nexus', spells.get('nexus').get('slot'))
        memspell('twi', spells.get('twi').get('slot'))

    press('ESC')


def keepalive():
    diff = datetime.datetime.now() - keep_alive.get('time')
    if q.qsize() == 0 and diff.seconds > (600 + random.randint(1, 10)):
        print('keep alive: ' + str(datetime.datetime.now()))
        q.put({'type': 'keep_alive', 'phrase': None, 'name': None})
        # stand()
        # sit()
        keep_alive['time'] = datetime.datetime.now()
        print_stats()


def init():
    print('Script starting. Make EQ active window now!')
    time.sleep(10)
    stand()
    sit()
    loaddefaultspells('velious')


if __name__ == "__main__":
    log_filepath = ("C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/Logs/eqlog_Melz_teek.txt")
    roster_filepath = "C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/"
    roster_filename_default = "gr.txt"
    log_file_path = "jmq.log"
    roster = {'names': []}

    spell_slot_keys = {1: '2', 2: '3', 3: '4', 4: '5', 5: '7', 6: '8', 7: '9', 8: '0'}

    # slot is spell gem slot that spell should be memmed to every time.
    #
    spells = {
        'gopt': {'slot': 2, 'casttime': 4.0, 'recasttime': 1.5},
        'vog': {'slot': 3, 'casttime': 6.0, 'recasttime': 3.0},
        'gob': {'slot': 4, 'casttime': 5.0, 'recasttime': 1.5},
        'grm': {'slot': 6, 'casttime': 6.0, 'recasttime': 1.5}
    }

    spell_ids = {'gopt': '1695', 'vog': '1710', 'gob': '1410', 'grm': '72'}

    master_phrase_map = {'gopt': 'gopt', 'vog': 'vog', 'gob': 'gob', 'grm': 'grm', 'c': 'gopt', 'clarity': 'gopt',
                         'c2': 'gopt', 'haste': 'vog'}

    # must be grouped to cast these spells
    group_spells = []

    memorized_spells = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None}
    last_cast_time = {}

    stats = {'requests': 0, 'processed': 0, 'ignored': 0}

    keep_alive = {'time': datetime.datetime.now()}

    q = queue.Queue()
    q_list = {'items': []}

    init()

    # Start the log monitor thread
    log_monitor_thread = threading.Thread(target=monitor_log, args=(log_filepath, q))
    log_monitor_thread.daemon = True
    log_monitor_thread.start()

    # Start the queue processing thread
    queue_processor_thread = threading.Thread(target=process_queue, args=(q,))
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
