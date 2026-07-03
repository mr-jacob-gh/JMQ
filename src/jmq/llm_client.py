import json
import re
import threading
import urllib.error
import urllib.request

from jmq import config, state, zones, druid_spells
from jmq.utils import write_to_log, write_conversation_history


def _log(message):
    print('[llm_client] ' + message)
    write_to_log('[llm_client] ' + message)


def _post_chat_completion(messages, model, base_url, timeout):
    url = base_url.rstrip('/') + '/chat/completions'
    payload = {'model': model, 'messages': messages}
    payload.update(config.lm_studio_extra_body)
    body = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        url, data=body, headers={'Content-Type': 'application/json'}, method='POST'
    )
    _log(f'POST {url} (model={model})')
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode('utf-8'))
    return payload['choices'][0]['message']['content']


def _run(messages, model, base_url, timeout, callback):
    try:
        reply = _post_chat_completion(messages, model, base_url, timeout)
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        _log(f'llm request failed: HTTP {e.code} {e.reason} - {detail}')
        if callback:
            callback(None, e)
        return
    except (urllib.error.URLError, KeyError, IndexError, ValueError) as e:
        _log(f'llm request failed: {e}')
        if callback:
            callback(None, e)
        return
    except Exception as e:
        # Broad catch is intentional: this runs on a background thread, so
        # without it an unexpected error would otherwise disappear silently
        # instead of reaching the caller's callback.
        _log(f'llm request failed unexpectedly: {type(e).__name__}: {e}')
        if callback:
            callback(None, e)
        return

    _log('llm reply received: ' + reply[:200])
    if callback:
        callback(reply, None)


def send_prompt(prompt, callback=None, model=None, base_url=None, timeout=60, system_prompt=None, history=None):
    """Send a prompt to the LM Studio server on a background thread.

    Returns immediately; normal program execution continues while the
    request is in flight. If provided, callback(reply, error) is invoked
    from the background thread once the request completes. Pass
    system_prompt (e.g. from a PersonaTemplate.render()) to set the
    chatbot's persona for this request. Pass history (a list of prior
    {'role': ..., 'content': ...} messages, e.g. from get_history()) to
    give the model context from earlier turns.
    """
    resolved_model = model or config.lm_studio_model
    resolved_base_url = base_url or config.lm_studio_base_url
    _log(f'queuing request to {resolved_base_url} (model={resolved_model}): {prompt[:200]!r}')

    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    if history:
        messages.extend(history)
    messages.append({'role': 'user', 'content': prompt})
    thread = threading.Thread(
        target=_run,
        args=(messages, resolved_model, resolved_base_url, timeout, callback),
        daemon=True,
    )
    thread.start()
    return thread


def get_history(name):
    return state.conversation_history.get(name, [])


def record_exchange(name, user_message, assistant_reply):
    history = state.conversation_history.setdefault(name, [])
    history.append({'role': 'user', 'content': user_message})
    history.append({'role': 'assistant', 'content': assistant_reply})
    del history[:-config.max_conversation_history]
    write_conversation_history()
    _log(f'recorded exchange for {name}')


def send_prompt_for(name, prompt, callback=None, model=None, base_url=None, timeout=60, system_prompt=None):
    """Like send_prompt, but automatically loads and updates the
    conversation history for a specific person (e.g. a player name), so
    each reply has context from that person's prior turns.
    """
    _log(f'sending prompt for {name}: {prompt[:200]!r}')

    def _on_complete(reply, error):
        if reply is not None:
            record_exchange(name, prompt, reply)
        if callback:
            callback(reply, error)

    return send_prompt(
        prompt,
        callback=_on_complete,
        model=model,
        base_url=base_url,
        timeout=timeout,
        system_prompt=system_prompt,
        history=get_history(name),
    )


SPELL_CLASSIFIER_SYSTEM_PROMPT = (
    "You are a message classifier for an EverQuest guild assistant bot. The player's message did "
    "not match any known spell phrase. Two things to work out:\n\n"
    "1. Spell match: they may be trying to request one of the following spells but misspelled or "
    "misworded it. Each spell is listed below by its canonical key, followed by known aliases in "
    "parentheses:\n\n{options}\n\n"
    "Decide which spell, if any, the player most likely meant. Be strict: a real word or common "
    "English word that merely happens to share a few letters, a prefix, or a similar sound with a "
    "spell key/alias is NOT evidence of a match on its own - it's a coincidence, and should get spell "
    "null and confidence 0. Only treat it as a match if it looks like a genuine typo, dropped/swapped "
    "letter, missing space, phonetic misspelling, or known shorthand OF that specific alias - i.e. "
    "something a human would recognize as clearly the same word gone wrong, not just a lookalike. "
    "When you do find a match, calibrate confidence to how close it actually is:\n"
    "90-100: near-identical to an alias/key (single typo, transposed letters, missing/extra letter).\n"
    "70-89: clearly the same word once you account for common shorthand, phonetic spelling, or a "
    "missing space (e.g. 'complete heal' -> 'ch').\n"
    "Below 70: don't guess - respond with spell null and confidence 0 instead of a low-confidence "
    "spell.\n"
    "Examples of NON-matches (respond null, confidence 0): 'potato' does NOT match 'potg' just "
    "because it starts with 'pot' - potato is a real, unrelated word. 'butt' does NOT match 'bb' just "
    "because they share letters - it's an unrelated word/insult, not a mangled version of 'bb'. "
    "'ronaldo' does NOT match anything just because it's a name.\n\n"
    "2. Coherence: separately, score whether the message contains ANY recognizable language - real "
    "words, common abbreviations, leetspeak, game slang, or profanity - no matter how short, rude, "
    "crude, low-effort, or off-topic. Recognizable language of any kind means HIGH coherence "
    "(80-100), even if it's just one word, a greeting, an insult, dirty talk, or barely related to "
    "spells at all. Only score LOW coherence (0-20) when the message is truly unintelligible: random "
    "keyboard mashing, a string of unrelated symbols/characters, or garbled text with no real words "
    "in it whatsoever. When in doubt, score coherence HIGH - it should only come out low if a human "
    "reading it could not identify a single real word.\n"
    "Examples: 'sow plz' -> coherence 95. 'yo bitch where my buffs at' -> coherence 100 (profanity "
    "still counts as language). 'lol' -> coherence 90. 'asdkjfh qwoeiur zzxc' -> coherence 5. "
    "'ronaldo' -> coherence 85 (a real word/name, even if unrelated).\n\n"
    "Respond with ONLY a JSON object, no other text, in the exact form {{\"spell\": "
    "\"<canonical_key_or_null>\", \"confidence\": <integer 0-100>, \"coherence\": <integer 0-100>}}. "
    "confidence is your certainty, from 0 to 100, that the chosen spell is what the player meant "
    "(0 if spell is null). If nothing plausibly matches, respond with spell null and confidence 0, "
    "but still score coherence on its own using the rubric above."
)


def _spell_options_text():
    grouped = {}
    for phrase, spell in config.master_phrase_map.items():
        grouped.setdefault(spell, set()).add(phrase)
    lines = []
    for spell in sorted(grouped):
        aliases = set(grouped[spell]) | set(druid_spells.get_spell_names(spell))
        aliases = sorted(alias for alias in aliases if alias != spell)
        lines.append(f'{spell} ({", ".join(aliases)})' if aliases else spell)
    return '\n'.join(lines)


def _parse_spell_classification(reply):
    match = re.search(r'\{.*\}', reply, re.DOTALL)
    if not match:
        return None, 0, 0
    try:
        data = json.loads(match.group(0))
    except (json.JSONDecodeError, TypeError):
        return None, 0, 0

    spell = data.get('spell')
    confidence = data.get('confidence')
    coherence = data.get('coherence')
    if not isinstance(confidence, (int, float)):
        confidence = 0
    if not isinstance(coherence, (int, float)):
        coherence = 0
    if spell not in config.spells:
        spell = None
    return spell, confidence, coherence


def classify_spell_phrase(phrase, callback):
    """Ask the LLM whether an unrecognized phrase was likely a misspelled spell request, and
    separately whether it's even a coherent, on-topic message worth replying to.

    callback(spell, confidence, coherence, error) is invoked from a background thread once the
    classification completes. spell is a canonical key from config.spells (or None), confidence
    is an integer 0-100 for the spell match, and coherence is an integer 0-100 for how much the
    message reads like a real, on-topic message rather than noise.
    """
    system_prompt = SPELL_CLASSIFIER_SYSTEM_PROMPT.format(options=_spell_options_text())

    def _on_reply(reply, error):
        if error or not reply:
            callback(None, 0, 0, error)
            return
        spell, confidence, coherence = _parse_spell_classification(reply)
        _log(
            f'spell classification for {phrase!r}: spell={spell!r}, confidence={confidence}, '
            f'coherence={coherence}'
        )
        callback(spell, confidence, coherence, None)

    send_prompt(phrase, callback=_on_reply, system_prompt=system_prompt)


ZONE_CLASSIFIER_SYSTEM_PROMPT = (
    "You are a message classifier for an EverQuest guild assistant bot. The player's message did "
    "not match any known spell request. Work out whether they are instead naming or describing an "
    "EverQuest zone, likely asking for a port/travel there. Here is the list of valid zone names:\n\n"
    "{options}\n\n"
    "Decide which zone, if any, the player most likely meant. Be strict: only pick a zone if the "
    "message clearly names it, a common abbreviation/nickname for it, or a close misspelling of it - "
    "a coincidental shared word or letters is NOT evidence of a match. If nothing plausibly names a "
    "zone, respond with zone null and confidence 0.\n"
    "Calibrate confidence to how close the match is:\n"
    "90-100: the exact zone name, a well-known nickname/abbreviation, or a single-typo variant.\n"
    "70-89: clearly the same zone once you account for shorthand or a missing word (e.g. 'ro' could "
    "be either desert of ro zone - only use this range if genuinely ambiguous).\n"
    "Below 70: don't guess - respond with zone null and confidence 0 instead of a low-confidence "
    "zone.\n\n"
    "Respond with ONLY a JSON object, no other text, in the exact form {{\"zone\": "
    "\"<exact_zone_name_or_null>\", \"confidence\": <integer 0-100>}}. The zone value must exactly "
    "match one of the names in the list above, or be null."
)


def _zone_options_text():
    return '\n'.join(zones.ZONE_NAMES)


def _parse_zone_classification(reply):
    match = re.search(r'\{.*\}', reply, re.DOTALL)
    if not match:
        return None, 0
    try:
        data = json.loads(match.group(0))
    except (json.JSONDecodeError, TypeError):
        return None, 0

    zone = data.get('zone')
    confidence = data.get('confidence')
    if not isinstance(confidence, (int, float)):
        confidence = 0
    if zone not in zones.ZONE_NAMES:
        zone = None
    return zone, confidence


def classify_zone_phrase(phrase, callback):
    """Ask the LLM whether an unrecognized phrase (that didn't match a spell) is naming an
    EverQuest zone the player wants a port to.

    callback(zone, confidence, error) is invoked from a background thread once the
    classification completes. zone is an exact name from zones.ZONE_NAMES (or None), and
    confidence is an integer 0-100.
    """
    system_prompt = ZONE_CLASSIFIER_SYSTEM_PROMPT.format(options=_zone_options_text())

    def _on_reply(reply, error):
        if error or not reply:
            callback(None, 0, error)
            return
        zone, confidence = _parse_zone_classification(reply)
        _log(f'zone classification for {phrase!r}: zone={zone!r}, confidence={confidence}')
        callback(zone, confidence, None)

    send_prompt(phrase, callback=_on_reply, system_prompt=system_prompt)
