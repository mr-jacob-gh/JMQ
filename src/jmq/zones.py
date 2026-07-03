import json
from pathlib import Path

from jmq import config

_ZONE_DATA_PATH = Path(__file__).resolve().parent.parent.parent / 'eqarchives_zone_adjacency.json'

with open(_ZONE_DATA_PATH, 'r', encoding='utf-8') as _f:
    _ZONE_DATA = json.load(_f)

_ZONES_BY_NAME = {zone['name']: zone for zone in _ZONE_DATA['zones']}

ZONE_NAMES = sorted(_ZONES_BY_NAME)


def get_nearest_druid_port(zone_name, castable_spells=None):
    """Look up the nearest druid port for a zone name (must match ZONE_NAMES exactly).

    Returns {'port_zone': str, 'spell': str, 'hops': int} or None if the zone is
    unknown or has no druid port path. If castable_spells is given (e.g.
    config.spells), the returned spell is filtered to one present in it -
    preferring a solo-castable spell over a group-only one - or None if none
    of the candidate spells are castable.
    """
    zone = _ZONES_BY_NAME.get(zone_name)
    if zone is None:
        return None

    if zone.get('druid_port'):
        port_zone = zone['name']
        hops = 0
        candidates = zone.get('druid_port_spells') or []
    else:
        port_zone = zone.get('nearest_druid_port_zone')
        hops = zone.get('nearest_druid_port_hops')
        candidates = zone.get('nearest_druid_port_spells') or []

    if not port_zone or not candidates:
        return None

    spell = _pick_spell(candidates, castable_spells)
    if spell is None:
        return None

    return {'port_zone': port_zone, 'spell': spell, 'hops': hops}


def _pick_spell(candidates, castable_spells):
    if castable_spells is not None:
        candidates = [spell for spell in candidates if spell in castable_spells]
    if not candidates:
        return None

    group_spells = set(config.group_spells)
    for spell in candidates:
        if spell not in group_spells:
            return spell
    return candidates[0]
