spells = {
    'reso': {'slot': 6, 'casttime': 3.5, 'recasttime': 1.5},
    'abolishpoison': {'slot': 6, 'casttime': 6.0, 'recasttime': 1.5},
    'naltron': {'slot': 6, 'casttime': 5.0, 'recasttime': 1.5},
    'armor': {'slot': 6, 'casttime': 6.0, 'recasttime': 1.5},
    'valor': {'slot': 6, 'casttime': 3.0, 'recasttime': 1.5},
    'pinzarn': {'slot': 6, 'casttime': 4.5, 'recasttime': 1.5},
    'heroism': {'slot': 6, 'casttime': 3.5, 'recasttime': 1.5},
    'marzin': {'slot': 6, 'casttime': 5.0, 'recasttime': 1.5},
    'fortitude': {'slot': 6, 'casttime': 7.0, 'recasttime': 1.5},
    'aegis': {'slot': 6, 'casttime': 7.0, 'recasttime': 1.5},
    'bulwark': {'slot': 6, 'casttime': 7.0, 'recasttime': 1.5},
    'gnaltron': {'slot': 6, 'casttime': 5.0, 'recasttime': 1.5},
    'aego': {'slot': 6, 'casttime': 14.0, 'recasttime': 1.5},
}

spell_ids = {
    'reso': '314',
    'abolishpoison': '97',
    'naltron': '488',
    'armor': '19',
    'valor': '312',
    'pinzarn': '487',
    'heroism': '1533',
    'marzin': '1535',
    'fortitude': '1539',
    'aegis': '1540',
    'bulwark': '1537',
    'gnaltron': '1774',
    'aego': '1447',
}

master_phrase_map = {
    'reso': 'reso', 'resolution': 'reso',
    'abolishpoison': 'abolishpoison', 'abolish poison': 'abolishpoison', 'abolish': 'abolishpoison',
    'naltron': 'naltron', 'symbol': 'naltron',
    'armor': 'armor',
    'valor': 'valor',
    'pinzarn': 'pinzarn',
    'heroism': 'heroism',
    'marzin': 'marzin',
    'fortitude': 'fortitude',
    'aegis': 'aegis',
    'bulwark': 'bulwark',
    'gnaltron': 'gnaltron',
    'aegolism': 'aego', 'aego': 'aego'
}

# must be grouped to cast these spells
group_spells = []

# spells to memorize by default, keyed by expansion
default_spells = {
    'kunark': [],
    'velious': ['aego'],
    'luclin': ['aego'],
}
