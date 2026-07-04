from pathlib import Path

# Loads the markdown persona template from the project root and exposes a
# render() interface so this is a drop-in replacement for zlem_persona.zlem
# at the call site in log_monitor.py. To switch back to the old
# PersonaTemplate-based persona, just change that import back.
_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / 'zlem_everquest_druid_persona_template_v4.md'
ZLEM_SYSTEM_PROMPT = _TEMPLATE_PATH.read_text(encoding='utf-8')


class ZlemPersonaV3:
    def render(self, context=None):
        if not context:
            return ZLEM_SYSTEM_PROMPT
        situation_bits = [
            f"{str(key).replace('_', ' ').capitalize()}: {value}" for key, value in context.items() if value
        ]
        if not situation_bits:
            return ZLEM_SYSTEM_PROMPT
        return ZLEM_SYSTEM_PROMPT + '\n\nCurrent situation:\n' + '\n'.join(situation_bits)


zlem_v3 = ZlemPersonaV3()
