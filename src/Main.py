import queue
import threading
from pathlib import Path

import pydirectinput
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
                    if 'vip' in line.lower():
                        while not q.empty():
                            q.get_nowait()
                            q.task_done()

                        q.put({'type': 'spell', 'phrase': match, 'name': name})
                        for item, index in q_list.get('items'):
                            if index != 0:
                                q.put(item)
                    else:
                        q.put({'type': 'spell', 'phrase': match, 'name': name})

                    q_list.get('items').append({'type': 'spell', 'phrase': match, 'name': name})
                else:
                    print('ignored message: ' + line)
                    stats['ignored'] = stats.get('ignored') + 1
            elif 'has joined your guild' in line or 'no longer a member of your guild' in line:
                q.put({'type': 'updateroster', 'phrase': None, 'name': None})
            elif 'updateroster' in line:
                updateroster()
            elif 'Outputfile Complete' in line:
                filename = line.split(': ')[1].strip('\n')
                roster['names'] = extract_guild_roster(roster_filepath + filename)
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
                pydirectinput.press('shift')
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


def process_group_spell(name, phrase):
    pydirectinput.press('enter')
    pydirectinput.write('/invite ')
    pydirectinput.keyDown('shift')
    pydirectinput.write(name[0].lower())
    pydirectinput.keyUp('shift')
    pydirectinput.write(name)
    pydirectinput.press('enter')
    # pydirectinput.press('enter')
    # pydirectinput.write('/tt accept invite casting in 5sec')
    # pydirectinput.press('enter')
    pydirectinput.press('-')
    time.sleep(5)
    castspell(phrase)
    pydirectinput.press('enter')
    pydirectinput.write('/disband')
    pydirectinput.press('enter')
    pydirectinput.press('enter')
    pydirectinput.write('/raiddisband')
    pydirectinput.press('enter')


def notify_queue_position(name, phrase, pos):
    send_tell(name, phrase + ' in queue at pos: ' + str(pos))


def process_spell_request(name, phrase):
    print('casting ' + phrase + ' on ' + name)
    # clear target
    pydirectinput.press('esc')
    # activate chat window
    pydirectinput.press('enter')
    # target the player
    pydirectinput.write('/tar ')
    pydirectinput.keyDown('shift')
    pydirectinput.write(name[0].lower())
    pydirectinput.keyUp('shift')
    pydirectinput.write(name)
    pydirectinput.press('enter')

    if phrase in group_spells:
        process_group_spell(name, phrase)
    else:
        # pydirectinput.press('enter')
        # pydirectinput.write('/tt ' + phrase + ' inc')
        # pydirectinput.press('enter')
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
    pydirectinput.press('enter')
    pydirectinput.write('/tell ')
    pydirectinput.keyDown('shift')
    pydirectinput.write(name[0].lower())
    pydirectinput.keyUp('shift')
    pydirectinput.write(name)
    pydirectinput.write(' ' + msg)
    pydirectinput.press('enter')
    keep_alive['time'] = datetime.datetime.now()


def sit():
    pydirectinput.press('enter', 1, 0.0)
    pydirectinput.write('/sit', 0.0)
    pydirectinput.press('enter', 1, 0.0)


def stand():
    pydirectinput.press('enter', 1, 0.0)
    pydirectinput.write('/stand', 0.0)
    pydirectinput.press('enter', 1, 0.0)


def clearspell(slot):
    pydirectinput.press('enter', 1, 0.0)
    pydirectinput.write('/memspellslot ' + str(slot) + ' ' + '0', 0.0)
    pydirectinput.press('enter', 1, 0.0)


def memspell(spell, slot):
    # print('spell in slot: '+str(slot)+' is '+str(memorized_spells.get(slot)))
    #  clearspell(slot)
    # can't have anything on cursor when trying to mem spells, stop mod rods from breaking script
    pydirectinput.press('enter', 1, 0.0)
    pydirectinput.write('/autoinv', 0.0)
    pydirectinput.press('enter', 1, 0.0)
    # mem the spell
    pydirectinput.press('enter', 1, 0.0)
    pydirectinput.write('/memspellslot ' + str(slot) + ' ' + spell_ids.get(spell), 0.0)
    pydirectinput.press('enter', 1, 0.0)
    # accounts for spellbar cooldown timer

    time.sleep(2.0)
    memorized_spells[slot] = spell
    last_cast_time[spell] = datetime.datetime.now()
    # print(spell + ' memorized')


def castspell(spell):
    slot = spells.get(spell).get('slot')
    if memorized_spells.get(slot) != spell:
        pydirectinput.press('1', 1, 0.0)
        memspell(spell, spells.get(spell).get('slot'))
        if slot == 8:
            tell_spell_inc(spell)
    else:
        if slot == 8:
            tell_spell_inc(spell)

    if last_cast_time.get(spell) is not None:
        diff = datetime.datetime.now() - last_cast_time.get(spell)
        if diff.seconds < spells.get(spell).get('recasttime'):
            time.sleep((spells.get(spell).get('recasttime') - diff.seconds) + 2.0)
            # print('pausing for recast time')

    print('now casting: ' + spell)
    key = spell_slot_keys.get(spells.get(spell).get('slot'))
    pydirectinput.press(key, 1, 0.0)
    time.sleep(spells.get(spell).get('casttime') + 2.0)
    last_cast_time[spell] = datetime.datetime.now()


def tell_spell_inc(spell):
    pydirectinput.press('enter')
    pydirectinput.write('/tt ' + spell + ' inc')
    pydirectinput.press('enter')


def updateroster():
    pydirectinput.press('enter', 1, 0.0)
    pydirectinput.write('/outputfile guild', 0.0)
    pydirectinput.press('enter', 1, 0.0)


def loaddefaultspells():
    memspell('heal', spells.get('heal').get('slot'))
    memspell('sow', spells.get('sow').get('slot'))
    memspell('potg', spells.get('potg').get('slot'))
    memspell('feerrott', spells.get('feerrott').get('slot'))
    memspell('cl', spells.get('cl').get('slot'))
    memspell('gd', spells.get('gd').get('slot'))
    memspell('cs', spells.get('cs').get('slot'))


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
    loaddefaultspells()


if __name__ == "__main__":
    log_filepath = "C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/Logs/eqlog_Zlem_oakwynd.txt"
    roster_filepath = "C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/"
    roster_filename_default = "Relentless Insomnia_oakwynd-default.txt"
    log_file_path = "jmq.log"
    roster = {'names': []}

    spell_slot_keys = {1: '2', 2: '3', 3: '4', 4: '5', 5: '7', 6: '8', 7: '9', 8: '0'}

    # slot is spell gem slot that spell should be memmed to every time.
    #
    spells = {
        'heal': {'slot': 1, 'casttime': 3.8, 'recasttime': 1.5},
        'sow': {'slot': 2, 'casttime': 4.5, 'recasttime': 3.5},
        'potg': {'slot': 3, 'casttime': 6.0, 'recasttime': 18.0},
        'lev': {'slot': 8, 'casttime': 3.0, 'recasttime': 5.0},
        'cl': {'slot': 5, 'casttime': 10.0, 'recasttime': 6.0},
        'chloro': {'slot': 8, 'casttime': 6.0, 'recasttime': 1.5},
        'thorns': {'slot': 8, 'casttime': 3.0, 'recasttime': 1.5},
        'blades': {'slot': 8, 'casttime': 3.0, 'recasttime': 1.5},
        'regrowth': {'slot': 8, 'casttime': 6.0, 'recasttime': 1.5},
        'sln': {'slot': 8, 'casttime': 6.0, 'recasttime': 12.0},
        'natureskin': {'slot': 8, 'casttime': 6.0, 'recasttime': 1.5},
        'stormstrength': {'slot': 8, 'casttime': 5.0, 'recasttime': 1.5},
        'cs': {'slot': 7, 'casttime': 10.0, 'recasttime': 6.0},
        'gd': {'slot': 6, 'casttime': 10.0, 'recasttime': 6.0},
        'ic': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'wl': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'dl': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'bb': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'feerrott': {'slot': 4, 'casttime': 10.0, 'recasttime': 6.0},
        'nk': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'lava': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'misty': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'ro': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'steamfont': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'sfg': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'toxx': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'sf': {'slot': 8, 'casttime': 9.0, 'recasttime': 1.5},
        'ej': {'slot': 8, 'casttime': 9.0, 'recasttime': 1.5},
        'ba': {'slot': 8, 'casttime': 6.0, 'recasttime': 1.5},
        'invis': {'slot': 8, 'casttime': 5.0, 'recasttime': 1.5},
        'counteractdisease': {'slot': 8, 'casttime': 4.0, 'recasttime': 1.5},
        'resistdisease': {'slot': 8, 'casttime': 4.5, 'recasttime': 1.5}
    }

    spell_ids = {'heal': '1291', 'sow': '278', 'potg': '1442', 'cl': '25690', 'lev': '261',
                 'chloro': '145', 'thorns': '356', 'blades': '1560', 'regrowth': '1568', 'sln': '423',
                 'natureskin': '1559', 'stormstrength': '430', 'cs': '25693', 'gd': '25696',
                 'ic': '25698', 'wl': '25906', 'dl': '25694', 'bb': '25689', 'feerrott': '25695',
                 'nk': '25899', 'lava': '24771', 'misty': '25699', 'ro': '25901', 'steamfont': '25902',
                 'sfg': '25900', 'toxx': '25904', 'sf': '1736', 'ej': '1737', 'ba': '35', 'invis': '34',
                 'counteractdisease': '96', 'resistdisease': '63'}

    master_phrase_map = {'ds': 'blades',  # update to the highest version available
                         'dspl': 'blades',  # update to the highest version that will land on a lvl 1
                         'regen': 'regrowth',  # update to the highest version available
                         'regenpl': 'chloro',  # update to the highest version that will land on a lvl 1
                         'heal': 'heal', 'sow': 'sow', 'potg': 'potg', 'cl': 'cl', 'levi': 'lev', 'lev': 'lev',
                         'chloro': 'chloro', 'thorns': 'thorns', 'blades': 'blades', 'regrowth': 'regrowth',
                         'sln': 'sln', 'natureskin': 'natureskin', 'stormstrength': 'stormstrength', 'cs': 'cs',
                         'gd': 'gd', 'ic': 'ic', 'wl': 'wl', 'dl': 'dl', 'bb': 'bb', 'feerrott': 'feerrott',
                         'nk': 'nk', 'lava': 'lava', 'misty': 'misty', 'ro': 'ro', 'steamfont': 'steamfont',
                         'sfg': 'sfg', 'toxx': 'toxx', 'spirit of wolf': 'sow', 'glades': 'potg',
                         'protection of the glades': 'potg', 'ec': 'cl', 'commons': 'cl', 'commonlands': 'cl',
                         'common lands': 'cl', 'east commons': 'cl', 'levitate': 'lev', 'chloroplast': 'chloro',
                         'skin like nature': 'sln', 'cobalt scar': 'cs', 'northk': 'nk', 'north karana': 'nk',
                         'karana': 'nk', 'lavastorm': 'lava', 'lava storm': 'lava', 'misty thicket': 'misty',
                         'nro': 'ro', 'sro': 'ro', 'northro': 'ro', 'north ro': 'ro', 'northern desert of ro': 'ro',
                         'south ro': 'ro', 'sf': 'sf', 'steam font': 'steamfont', 'surefall': 'sfg',
                         'sure fall': 'sfg', 'surefall glade': 'sfg', 'surefallglade': 'sfg', 'toxxulia': 'toxx',
                         'toxxulia forest': 'toxx', 'great divide': 'gd', 'iceclad': 'ic', 'iceclad ocean': 'ic',
                         'icecladocean': 'ic', 'wakening lands': 'wl', 'wakeninglands': 'wl', 'dreadlands': 'dl',
                         'dread lands': 'dl', 'butcher': 'bb', 'butcherblock': 'bb', 'bbm': 'bb',
                         'butcherblock mountains': 'bb', 'butcher block': 'bb', 'ferrott': 'feerrott',
                         'feerott': 'feerrott', 'feerrot': 'feerrott', 'feerroot': 'feerrott', 'ferot': 'feerrott',
                         'tox': 'toxx', 'ferroot': 'feerrott', 'ej': 'ej', 'emerald jungle': 'ej', 'emerald': 'ej',
                         'skyfire': 'sf', 'sky fire': 'sf', 'skyfire mountains': 'sf', 'ba': 'ba', 'bind': 'ba',
                         'bind affinity': 'ba', 'fear': 'feerrott', 'invis': 'invis', 'camo': 'invis',
                         'camouflage': 'invis', 'superior camouflage': 'invis', 'counteractdisease': 'counteractdisease',
                         'cure disease': 'counteractdisease', 'resistdisease': 'resistdisease',
                         'resist disease': 'resistdisease', 'disease resist': 'resistdisease', 'fearrott': 'feerrott',
                         'ct': 'feerrott', 'mistythicket': 'misty'}

    group_spells = ['ej', 'sf', 'ba', 'invis']

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

    try:
        while True:
            time.sleep(10)
            keepalive()
    except KeyboardInterrupt:
        print("Stopping...")
    except Exception as e:
        print(e)
