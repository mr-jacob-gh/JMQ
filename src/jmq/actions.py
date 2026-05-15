import datetime

import pyKey
import time

from jmq import state


def press(key):
    pyKey.press(key)
    time.sleep(0.1)


def sit():
    press('ENTER')
    pyKey.sendSequence('/sit')
    press('ENTER')


def stand():
    press('ENTER')
    pyKey.sendSequence('/stand')
    press('ENTER')


def send_tell(name, msg):
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
    state.keep_alive['time'] = datetime.datetime.now()


def send_tell_to_current_target(msg):
    press('ENTER')
    pyKey.sendSequence('/tt')
    press('SPACEBAR')
    for token in msg.split(' '):
        pyKey.sendSequence(token)
        press('SPACEBAR')
    press('ENTER')
    state.keep_alive['time'] = datetime.datetime.now()


def send_status(name):
    if name in state.roster.get('names'):
        send_tell(name, 'online')


def notify_queue_position(name, phrase, pos):
    send_tell(name, phrase + ' in queue at pos: ' + str(pos))


def updateroster():
    print('updateroster')
    press('ENTER')
    pyKey.sendSequence('/outputfile')
    press('SPACEBAR')
    pyKey.sendSequence('guild')
    press('SPACEBAR')
    pyKey.sendSequence('gr')
    print('pause')
    press('ENTER')
