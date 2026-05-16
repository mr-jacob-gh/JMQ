import queue
import datetime

memorized_spells = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None}
last_cast_time = {}
stats = {'requests': 0, 'processed': 0, 'ignored': 0}
keep_alive = {'time': datetime.datetime.now()}
q = queue.Queue()
q_list = {'items': []}
roster = {'names': []}
failure_events = []
player_stats = {}
