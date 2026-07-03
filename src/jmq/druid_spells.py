import json
from pathlib import Path

_DRUID_SPELL_DATA_PATH = Path(__file__).resolve().parent.parent.parent / 'everquest_druid_spells.json'

with open(_DRUID_SPELL_DATA_PATH, 'r', encoding='utf-8') as _f:
    _DRUID_SPELL_DATA = json.load(_f)

_NAMES_BY_KEY = {}
for _spell in _DRUID_SPELL_DATA:
    for _key in _spell.get('config_keys') or []:
        _NAMES_BY_KEY.setdefault(_key, []).append(_spell['name'])


def get_spell_names(spell_key):
    """Return the canonical in-game name(s) from everquest_druid_spells.json for a config key
    (e.g. 'sow' -> ['Spirit of Wolf']), or an empty list if none are known.
    """
    return _NAMES_BY_KEY.get(spell_key, [])
