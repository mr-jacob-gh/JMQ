import json
from pathlib import Path

_DRUID_SPELL_DATA_PATH = Path(__file__).resolve().parent.parent.parent / 'everquest_druid_spells.json'

with open(_DRUID_SPELL_DATA_PATH, 'r', encoding='utf-8') as _f:
    _DRUID_SPELL_DATA = json.load(_f)

# Only spells with a config_keys entry are ones the bot actually knows how to cast.
_CASTABLE_SPELLS = [spell for spell in _DRUID_SPELL_DATA if spell.get('config_keys')]

DRUID_SPELL_NAMES = sorted(spell['name'] for spell in _CASTABLE_SPELLS)

_SPELL_KEYS_BY_NAME = {spell['name']: spell['config_keys'][0] for spell in _CASTABLE_SPELLS}


def get_spell_key(spell_name):
    """Map a canonical spell name (from DRUID_SPELL_NAMES) to its config key (the key used in
    config.spells/master_phrase_map), or None if the spell name is unknown.
    """
    return _SPELL_KEYS_BY_NAME.get(spell_name)
