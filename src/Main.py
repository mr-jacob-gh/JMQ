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
                q.put({'phrase': match, 'name': extract_name(line)})
            elif 'updateroster' in line:
                updateroster()
            elif 'Outputfile Complete' in line:
                filename = line.split(': ')[1].strip('\n')
                roster['names'] = extract_guild_roster(roster_filepath + filename)


def get_match(line):
    if 'tells you' not in line:
        return None

    # compare entire phrase to spell list
    start = line.index('\'') + 1
    end = len(line) - 2
    phrase = line[start:end].lower().strip('!?.,;@#$%^&*')
    if phrase in master_phrase_map.keys():
        return master_phrase_map.get(phrase)
    else:  # compare each word in phrase to spell list
        for word in phrase.split(' '):
            if word in master_phrase_map.keys():
                return master_phrase_map.get(word)

    return None


def process_queue(q):
    while True:
        task = q.get()  # This blocks until a new item is available in the queue
        phrase = task.get('phrase')
        print(f"Detected phrase: {phrase}")
        print(f"extracted name: {task.get('name')}")
        # only process queue items for guild members
        if task.get('name') not in roster.get('names'):
            q.task_done()
            continue

        # clear target
        pydirectinput.press('esc')
        # activate chat window
        pydirectinput.press('enter')
        # target the player
        pydirectinput.write('/target ')
        pydirectinput.keyDown('shift')
        pydirectinput.write(task.get('name')[0].lower())
        pydirectinput.keyUp('shift')
        pydirectinput.write(task.get('name'))
        pydirectinput.press('enter')
        pydirectinput.press('enter')
        pydirectinput.write('/tt ' + phrase + ' inc')
        pydirectinput.press('enter')
        # cast the spell
        castspell(phrase)
        q.task_done()
        if q.qsize() == 0:
            stand()
            sit()


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
    if memorized_spells.get(slot) != spell:
        clearspell(slot)
        pydirectinput.press('enter', 1, 0.0)
        pydirectinput.write('/memspellslot ' + str(slot) + ' ' + spell_ids.get(spell), 0.0)
        pydirectinput.press('enter', 1, 0.0)
        time.sleep(spells.get(spell).get('recasttime') + 4.0)
        memorized_spells[slot] = spell
        # print(spell + ' memorized')


def castspell(spell):
    memspell(spell, spells.get(spell).get('slot'))
    if last_cast_time.get(spell) is not None:
        diff = datetime.datetime.now() - last_cast_time.get(spell)
        if diff.seconds < spells.get(spell).get('recasttime'):
            time.sleep(spells.get(spell).get('recasttime') - diff.seconds)
            # print('pausing for recast time')

    print('now casting: ' + spell)
    key = spell_slot_keys.get(spells.get(spell).get('slot'))
    pydirectinput.press(key, 1, 0.0)
    time.sleep(spells.get(spell).get('casttime') + 2.0)
    last_cast_time[spell] = datetime.datetime.now()


def updateroster():
    pydirectinput.press('enter', 1, 0.0)
    pydirectinput.write('/outputfile guild', 0.0)
    pydirectinput.press('enter', 1, 0.0)


def loaddefaultspells():
    memspell('heal', spells.get('heal').get('slot'))
    memspell('sow', spells.get('sow').get('slot'))
    memspell('potg', spells.get('potg').get('slot'))
    memspell('levi', spells.get('levi').get('slot'))
    memspell('cl', spells.get('cl').get('slot'))
    memspell('gd', spells.get('gd').get('slot'))
    memspell('cs', spells.get('cs').get('slot'))


def keepalive():
    diff = datetime.datetime.now() - keep_alive.get('time')
    if diff.seconds > (600 + random.randint(1, 10)):
        print('keep alive')
        stand()
        sit()
        keep_alive['time'] = datetime.datetime.now()


def init():
    print('Script starting. Make EQ active window now!')
    time.sleep(10)
    stand()
    sit()
    updateroster()
    loaddefaultspells()
    time.sleep(6)


if __name__ == "__main__":
    log_filepath = "C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/Logs/eqlog_Zlem_oakwynd.txt"
    roster_filepath = "C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/"
    roster_filename_default = "Relentless Insomnia_oakwynd-default.txt"
    roster = {'names': []}

    spell_slot_keys = {1: '2', 2: '3', 3: '4', 5: '7', 6: '8', 7: '9', 8: '0'}

    # slot is spell gem slot that spell should be memmed to every time.
    #
    spells = {
        'heal': {'slot': 1, 'casttime': 3.8, 'recasttime': 1.5},
        'sow': {'slot': 2, 'casttime': 4.5, 'recasttime': 3.5},
        'potg': {'slot': 3, 'casttime': 6.0, 'recasttime': 18.0},
        'levi': {'slot': 4, 'casttime': 3.0, 'recasttime': 5.0},
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
        'feerrott': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'nk': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'lava': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'misty': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'ro': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'steamfont': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'sfg': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0},
        'toxx': {'slot': 8, 'casttime': 10.0, 'recasttime': 6.0}
    }

    spell_ids = {'heal': '1291', 'sow': '278', 'potg': '1442', 'cl': '25690', 'levi': '261',
                 'chloro': '145', 'thorns': '356', 'blades': '1560', 'regrowth': '1568', 'sln': '423',
                 'natureskin': '1559', 'stormstrength': '430', 'cs': '25693', 'gd': '25696',
                 'ic': '25698', 'wl': '25906', 'dl': '25694', 'bb': '25689', 'feerrott': '25695',
                 'nk': '25899', 'lava': '24771', 'misty': '25699', 'ro': '25901', 'steamfont': '25902',
                 'sfg': '25900', 'toxx': '25904'}

    master_phrase_map = {'heal': 'heal', 'sow': 'sow', 'potg': 'potg', 'cl': 'cl', 'levi': 'levi',
                         'chloro': 'chloro', 'thorns': 'thorns', 'blades': 'blades', 'regrowth': 'regrowth',
                         'sln': 'sln', 'natureskin': 'natureskin', 'stormstrength': 'stormstrength', 'cs': 'cs',
                         'gd': 'gd', 'ic': 'ic', 'wl': 'wl', 'dl': 'dl', 'bb': 'bb', 'feerrott': 'feerrott',
                         'nk': 'nk', 'lava': 'lava', 'misty': 'misty', 'ro': 'ro', 'steamfont': 'steamfont',
                         'sfg': 'sfg', 'toxx': 'toxx', 'spirit of wolf': 'sow', 'glades': 'potg',
                         'protection of the glades': 'potg', 'ec': 'cl', 'commons': 'cl', 'commonlands': 'cl',
                         'common lands': 'cl', 'east commons': 'cl', 'levitate': 'levi', 'chloroplast': 'chloro',
                         'skin like nature': 'sln', 'cobalt scar': 'cs', 'northk': 'nk', 'north karana': 'nk',
                         'karana': 'nk', 'lavastorm': 'lava', 'lava storm': 'lava', 'misty thicket': 'misty',
                         'nro': 'ro', 'sro': 'ro', 'northro': 'ro', 'north ro': 'ro', 'northern desert of ro': 'ro',
                         'south ro': 'ro', 'sf': 'steamfont', 'steam font': 'steamfont', 'surefall': 'sfg',
                         'sure fall': 'sfg', 'surefall glade': 'sfg', 'surefallglade': 'sfg', 'toxxulia': 'toxx',
                         'toxxulia forest': 'toxx', 'great divide': 'gd', 'iceclad': 'ic', 'iceclad ocean': 'ic',
                         'icecladocean': 'ic', 'wakening lands': 'wl', 'wakeninglands': 'wl', 'dreadlands': 'dl',
                         'dread lands': 'dl', 'butcher': 'bb', 'butcherblock': 'bb', 'bbm': 'bb',
                         'butcherblock mountains': 'bb', 'butcher block': 'bb', 'ferrott': 'feerrott',
                         'feerott': 'feerrott', 'feerrot': 'feerrott', 'feerroot': 'feerrott', 'ferot': 'feerrott'}

    memorized_spells = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None}
    last_cast_time = {}

    keep_alive = {'time': datetime.datetime.now()}

    q = queue.Queue()

    # Start the log monitor thread
    log_monitor_thread = threading.Thread(target=monitor_log, args=(log_filepath, q))
    log_monitor_thread.daemon = True
    log_monitor_thread.start()

    # Start the queue processing thread
    queue_processor_thread = threading.Thread(target=process_queue, args=(q,))
    queue_processor_thread.daemon = True
    queue_processor_thread.start()

    init()

    try:
        while True:
            time.sleep(10)
            keepalive()
    except KeyboardInterrupt:
        print("Stopping...")
    except Exception as e:
        print(e)
