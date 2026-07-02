log_filepath = "C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/Logs/eqlog_Zlem_frostreaver.txt"
roster_filepath = "C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/"
roster_filename_default = "gr.txt"
log_file_path = "jmq.log"
player_stats_file_path = "player_stats.json"
priority_queue_file_path = "priority_queue.json"

lm_studio_base_url = "http://192.168.50.175:1234/v1"
lm_studio_model = "qwen3.5-9b-ultra-uncensored-heretic-v2"
# Qwen3.5 supports a thinking/reasoning mode; disable it so replies come back quickly.
lm_studio_extra_body = {"chat_template_kwargs": {"enable_thinking": True}}
conversation_history_file_path = "conversation_history.json"
max_conversation_history = 20

spell_slot_keys = {1: '2', 2: '3', 3: '4', 4: '5', 5: '7', 6: '8', 7: '9', 8: '0'}

# Per-class spell data (spells, spell_ids, master_phrase_map, group_spells) is loaded
# from the matching <class>_config.py module at startup via main.load_class_config().
spells = {}
spell_ids = {}
master_phrase_map = {}
group_spells = []
default_spells = {}

failure_strings = [
    'spell fizzles',
    'You must first select a target for this spell!',
    "I don't see anyone by that name around here...",
    'Your spell is too powerful for your intended target.',
    'You have joined the group.',
    'You cannot memorize this spell.',
    'Insufficient Mana to cast this spell!',
    'To invite another group into yours, please invite the leader of the other group.',
    'Your target is out of range, get closer!',
    "You complete the trade with",
    "You are too far away"
]
