from jmq import state
from jmq.actions import press, send_status, updateroster, stand, sit, send_stats
from jmq.spells import process_spell_request
from jmq.utils import write_to_log


def process_queue(q):
    req_type = None
    phrase = None
    name = None
    timestamp = None
    while True:
        try:
            standsit = True
            task = q.get()  # This blocks until a new item is available in the queue
            req_type = task.get('type')
            phrase = task.get('phrase')
            name = task.get('name')
            timestamp = task.get('timestamp')
            write_to_log('processing queue task: ' + str(req_type) + ', ' + str(phrase) + ', ' + str(name))

            if req_type == 'spell':
                process_spell_request(name, phrase)
            elif req_type == 'status':
                send_status(name)
                standsit = False
            elif req_type == 'stats':
                send_stats(name)
                standsit = False
            elif req_type == 'totalstats':
                send_total_stats(name)
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
            for item in state.q_list.get('items'):
                if item.get('type') == req_type and item.get('phrase') == phrase and item.get('name') == name and item.get('timestamp') == timestamp:
                    state.q_list.get('items').remove(item)
                    break

        # q.task_done()
        if q.qsize() == 0 and standsit:
            stand()
            sit()


def add_item_to_queue(_type, phrase, name, timestamp):
    match = False
    for item in state.q_list.get('items'):
        if item.get('type') == _type and item.get('phrase') == phrase and item.get('name') == name:
            match = True
            break

    if not match:
        state.q.put({'type': _type, 'phrase': phrase, 'name': name, 'timestamp': timestamp})
        state.q_list['items'].append({'type': _type, 'phrase': phrase, 'name': name, 'timestamp': timestamp})


def already_in_queue(phrase, name):
    for item in state.q_list.get('items'):
        if item.get('type') == 'spell' and item.get('phrase') == phrase and item.get('name') == name:
            return True
    return False
