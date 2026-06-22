import datetime
import os
import time

import pyKey
import pyautogui

from jmq import config, state
from jmq.actions import press, send_tell_to_current_target, sit
from jmq.utils import write_player_stats


def clearspell(slot):
    press('ENTER')
    pyKey.sendSequence('/memspellslot')
    press('SPACEBAR')
    pyKey.sendSequence(str(slot))
    press('SPACEBAR')
    pyKey.sendSequence('0')
    press('ENTER')


def memspell(spell, slot):
    # can't have anything on cursor when trying to mem spells, stop mod rods from breaking script
    press('ENTER')
    pyKey.sendSequence('/autoinv')
    press('ENTER')
    press('ENTER')
    pyKey.sendSequence('/memspellslot')
    press('SPACEBAR')
    pyKey.sendSequence(str(slot))
    press('SPACEBAR')
    pyKey.sendSequence(config.spell_ids.get(spell))
    press('ENTER')
    time.sleep(0.5)
    if any('You cannot memorize this spell' in item['failure'] for item in state.failure_events):
        return
    # accounts for spellbar cooldown timer
    time.sleep(2.3)
    state.memorized_spells[slot] = spell
    state.last_cast_time[spell] = datetime.datetime.now()


def tell_spell_inc(spell):
    press('ENTER')
    pyKey.sendSequence('/tt')
    press('SPACEBAR')
    pyKey.sendSequence(spell)
    press('SPACEBAR')
    pyKey.sendSequence('inc')
    press('ENTER')


def castspell(spell):
    slot = config.spells.get(spell).get('slot')
    if state.memorized_spells.get(slot) != spell:
        send_tell_to_current_target('memorizing spell - one moment')
        memspell(spell, config.spells.get(spell).get('slot'))
        if any('You cannot memorize this spell' in item['failure'] for item in state.failure_events):
            state.failure_events.clear()
            send_tell_to_current_target('I don\'t have this spell memorized, sorry!')
            return

    if state.last_cast_time.get(spell) is not None:
        diff = datetime.datetime.now() - state.last_cast_time.get(spell)
        if diff.seconds < config.spells.get(spell).get('recasttime'):
            time.sleep((config.spells.get(spell).get('recasttime') - diff.seconds) + 1.0)

    print('now casting: ' + spell)
    tell_spell_inc(spell)
    pyKey.sendSequence('/cast')
    press('SPACEBAR')
    pyKey.sendSequence(str(config.spells.get(spell).get('slot')))
    press('ENTER')
    cast_time = config.spells.get(spell).get('casttime')
    focus_reduction = cast_time * 0.15
    # cast_time = cast_time - focus_reduction
    time.sleep(0.5)
    if any('You must first select a target for this spell' in item['failure'] for item in state.failure_events):
        state.failure_events.clear()
        return
    time.sleep(cast_time + 1.0)
    state.last_cast_time[spell] = datetime.datetime.now()


def process_group_spell(name, phrase):
    press('ENTER')
    pyKey.sendSequence('/disband')
    press('ENTER')
    time.sleep(1.0)
    press('ENTER')
    pyKey.sendSequence('/invite')
    press('SPACEBAR')
    pyKey.pressKey('LSHIFT')
    pyKey.sendSequence(name[0].lower())
    pyKey.releaseKey('LSHIFT')
    pyKey.sendSequence(name[1:])
    press('ENTER')
    time.sleep(1)
    if any('To invite another group into yours, please invite the leader of the other group.' in item['failure'] for item in state.failure_events):
        send_tell_to_current_target('You must be the leader of the group to request a group spell.')
        state.failure_events.clear()
        return
    send_tell_to_current_target('Accept group invite - casting in 5 seconds!')
    time.sleep(6)
    if not any('You have joined the group.' in item['failure'] for item in state.failure_events):
        send_tell_to_current_target('You did not join the group in time!')
        state.failure_events.clear()
        return

    castspell(phrase)
    press('ENTER')
    pyKey.sendSequence('/disband')
    press('ENTER')
    press('ENTER')
    pyKey.sendSequence('/raiddisband')
    press('ENTER')



def process_spell_request(name, phrase):
    print('casting ' + phrase + ' on ' + name)
    state.failure_events.clear()
    # clear target
    press('ESC')
    # activate chat window
    press('ENTER')
    # target the player
    pyKey.sendSequence('/tar')
    press('SPACEBAR')
    pyKey.pressKey('LSHIFT')
    pyKey.sendSequence(name[0].lower())
    time.sleep(0.1)
    pyKey.releaseKey('LSHIFT')
    pyKey.sendSequence(name[1:])
    time.sleep(0.1)
    press('ENTER')

    time.sleep(0.5)
    target_failure_strings = ['You must first select a target for this spell', "I don't see anyone by that name around here"]
    if any(any(f in item['failure'] for f in target_failure_strings) for item in state.failure_events):
        state.failure_events.clear()
        state.q_list['items'] = [item for item in state.q_list['items'] if item.get('name') != name]
        remaining = []
        while not state.q.empty():
            task = state.q.get_nowait()
            state.q.task_done()
            if task.get('name') != name:
                remaining.append(task)
        for task in remaining:
            state.q.put(task)
        return

    if phrase in config.group_spells:
        time.sleep(0.2)
        process_group_spell(name, phrase)
    else:
        time.sleep(0.2)
        castspell(phrase)

    time.sleep(0.5)
    for _ in range(2):
        if not any('spell fizzles' in item['failure'] and 'Your' in item['line'] for item in state.failure_events):
            break
        state.failure_events.clear()
        if phrase in config.group_spells:
            time.sleep(0.5)
            process_group_spell(name, phrase)
        else:
            time.sleep(0.5)
            castspell(phrase)

    time.sleep(0.5)
    for attempt in range(6):
        if not any('Insufficient Mana to cast this spell' in item['failure'] for item in state.failure_events):
            break
        if attempt == 0:
            sit()
            send_tell_to_current_target('low mana - will retry momentarily')
        if attempt == 5:
            send_tell_to_current_target('still not enough mana, please request again.')
            break
        state.failure_events.clear()
        if phrase in config.group_spells:
            time.sleep(5.0)
            process_group_spell(name, phrase)
        else:
            time.sleep(5.0)
            castspell(phrase)

    if any('Your spell is too powerful for your intended target' in item['failure'] for item in state.failure_events):
        send_tell_to_current_target(phrase + ' is too powerful for your level')

    range_failure_strings = ['Your target is out of range, get closer']
    if any(any(f in item['failure'] for f in range_failure_strings) for item in state.failure_events):
        send_tell_to_current_target('You were out of range for ' + phrase)

    state.failure_events.clear()
    state.player_stats.setdefault(name, {})
    state.player_stats[name][phrase] = state.player_stats[name].get(phrase, 0) + 1
    write_player_stats()
    state.keep_alive['time'] = datetime.datetime.now()
    state.stats['processed'] = state.stats.get('processed') + 1


def loaddefaultspells(xpac):
    for spell in config.default_spells.get(xpac, []):
        memspell(spell, config.spells.get(spell).get('slot'))

    press('ESC')


def send_food_or_drink(name, phrase):
    # time.sleep(5.0)
    print('creating ' + phrase + ' for ' + name)
    state.failure_events.clear()
    # clear target
    press('ESC')
    # activate chat window
    press('ENTER')
    # target the player
    pyKey.sendSequence('/tar')
    press('SPACEBAR')
    pyKey.pressKey('LSHIFT')
    pyKey.sendSequence(name[0].lower())
    time.sleep(0.1)
    pyKey.releaseKey('LSHIFT')
    pyKey.sendSequence(name[1:])
    time.sleep(0.1)
    press('ENTER')

    time.sleep(0.5)
    target_failure_strings = ['You must first select a target for this spell', "I don't see anyone by that name around here",
                              "You are too far away"]
    if any(any(f in item['failure'] for f in target_failure_strings) for item in state.failure_events):
        state.failure_events.clear()
        state.q_list['items'] = [item for item in state.q_list['items'] if item.get('name') != name]
        remaining = []
        while not state.q.empty():
            task = state.q.get_nowait()
            state.q.task_done()
            if task.get('name') != name:
                remaining.append(task)
        for task in remaining:
            state.q.put(task)
        pyKey.sendSequence('/destroyitem')
        time.sleep(0.1)
        press('ENTER')
        sit()
        return

    if state.last_cast_time.get(phrase) is not None:
        diff = datetime.datetime.now() - state.last_cast_time.get(phrase)
        if diff.seconds < 10.0:
            time.sleep((10.0 - diff.seconds) + 1.0)

    if phrase == "food":
        press('1')
    if phrase == "drink":
        press('2')

    time.sleep(1.5)
    state.last_cast_time[phrase] = datetime.datetime.now()
    pyKey.sendSequence('/uset')
    time.sleep(0.1)
    press('ENTER')
    time.sleep(1.0)
    target_failure_strings = ["You are too far away"]
    if any(any(f in item['failure'] for f in target_failure_strings) for item in state.failure_events):
        send_tell_to_current_target('You were out of range for the trade.')
        state.failure_events.clear()
        state.q_list['items'] = [item for item in state.q_list['items'] if item.get('name') != name]
        remaining = []
        while not state.q.empty():
            task = state.q.get_nowait()
            state.q.task_done()
            if task.get('name') != name:
                remaining.append(task)
        for task in remaining:
            state.q.put(task)
        pyKey.sendSequence('/destroyitem')
        time.sleep(0.1)
        press('ENTER')
        sit()
        return

    #mouse click accept
    #pyautogui.moveTo(53, 361)
    time.sleep(1.5)
    try:
        pyautogui.click(os.path.join(os.path.dirname(__file__), '..', 'resources', 'trade.png'))
    except Exception as e:
        print(f'pyautogui.click trade.png failed: {e}')
    time.sleep(0.1)
    pyautogui.mouseUp()
    send_tell_to_current_target("You have 5 seconds to accept the trade!")
    time.sleep(5.0)
    if not any('You complete the trade with' in item['failure'] for item in state.failure_events):
        send_tell_to_current_target("You did not accept the trade in time.")
        # mouse click cancel
        #pyautogui.moveTo(185, 361)
        time.sleep(0.1)
        try:
            pyautogui.click(os.path.join(os.path.dirname(__file__), '..', 'resources', 'cancel.png'))
        except Exception as e:
            print(f'pyautogui.click cancel.png failed: {e}')
        time.sleep(0.1)
        pyautogui.mouseUp()

    pyKey.sendSequence('/destroyitem')
    time.sleep(0.1)
    press('ENTER')

    state.failure_events.clear()
    state.player_stats.setdefault(name, {})
    state.player_stats[name][phrase] = state.player_stats[name].get(phrase, 0) + 1
    write_player_stats()
    state.keep_alive['time'] = datetime.datetime.now()
    state.stats['processed'] = state.stats.get('processed') + 1
    sit()