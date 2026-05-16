import datetime
import time

import pyKey

from jmq import config, state
from jmq.actions import press, send_tell, send_tell_to_current_target
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


def tell_spell_too_powerful(name, phrase):
    send_tell_to_current_target(phrase + ' is too powerful for your level')


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
    press('ENTER')
    pyKey.sendSequence('/invite')
    press('SPACEBAR')
    pyKey.pressKey('LSHIFT')
    pyKey.sendSequence(name[0].lower())
    pyKey.releaseKey('LSHIFT')
    pyKey.sendSequence(name[1:])
    press('ENTER')
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

    if any('Your spell is too powerful for your intended target' in item['failure'] for item in state.failure_events):
        tell_spell_too_powerful(name, phrase)

    state.failure_events.clear()
    state.player_stats.setdefault(name, {})
    state.player_stats[name][phrase] = state.player_stats[name].get(phrase, 0) + 1
    write_player_stats()
    state.keep_alive['time'] = datetime.datetime.now()
    state.stats['processed'] = state.stats.get('processed') + 1


def loaddefaultspells(xpac):
    if xpac == 'kunark':
        memspell('heal', config.spells.get('heal').get('slot'))
        memspell('sow', config.spells.get('sow').get('slot'))
        memspell('natureskin', config.spells.get('natureskin').get('slot'))
        memspell('feerrott', config.spells.get('feerrott').get('slot'))
        memspell('bb', config.spells.get('bb').get('slot'))
        memspell('sf', config.spells.get('sf').get('slot'))
        memspell('ej', config.spells.get('ej').get('slot'))
        memspell('toxx', config.spells.get('toxx').get('slot'))

        #memspell('sf', config.spells.get('sf').get('slot'))
    elif xpac == 'velious':
        memspell('heal', config.spells.get('heal').get('slot'))
        memspell('sow', config.spells.get('sow').get('slot'))
        memspell('potg', config.spells.get('potg').get('slot'))
        memspell('feerrott', config.spells.get('feerrott').get('slot'))
        memspell('cl', config.spells.get('cl').get('slot'))
        memspell('gd', config.spells.get('gd').get('slot'))
        memspell('cs', config.spells.get('cs').get('slot'))
    elif xpac == 'luclin':
        memspell('heal', config.spells.get('heal').get('slot'))
        # memspell('soe', config.spells.get('soe').get('slot'))
        # memspell('potc', config.spells.get('potc').get('slot'))
        memspell('soe', config.spells.get('soe').get('slot'))
        memspell('pot9', config.spells.get('pot9').get('slot'))
        memspell('cl', config.spells.get('cl').get('slot'))
        # memspell('dawn', config.spells.get('dawn').get('slot'))
        memspell('grim', config.spells.get('grim').get('slot'))
        memspell('replenishment', config.spells.get('replenishment').get('slot'))
        memspell('twi', config.spells.get('twi').get('slot'))

    press('ESC')
