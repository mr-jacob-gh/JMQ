from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

# Render order, highest priority first. When render() is given a max_chars
# budget, sections are trimmed off the end of this order (lowest priority)
# until the prompt fits.
DEFAULT_SECTION_PRIORITY = [
    'identity',
    'hard_rules',
    'personality',
    'emotional_dynamics',
    'speech_style',
    'relationship',
    'soft_preferences',
    'knowledge',
    'situation',
    'sample_exchanges',
]


@dataclass
class PersonaTemplate:
    """Fill in the fields below one section at a time, then call render()
    to get the system prompt for send_prompt(..., system_prompt=...).

    render() takes an optional `context` dict for per-request details that
    shouldn't be baked into the static persona (e.g. the current player's
    name/familiarity), and an optional `max_chars` budget that trims the
    lowest-priority sections first if the rendered prompt runs long.

    with_mode(name) returns a copy of this persona with the field overrides
    from `variants[name]` applied, for persona presets (e.g. a calmer or
    more hyped-up version of the same character).
    """

    # -- Core identity ---------------------------------------------------
    name: str = ""
    race: str = ""
    char_class: str = ""
    age: str = ""
    appearance: str = ""
    backstory: str = ""
    motivation: str = ""
    values: List[str] = field(default_factory=list)

    # -- Personality mechanics --------------------------------------------
    primary_traits: List[str] = field(default_factory=list)
    contrasting_traits: List[str] = field(default_factory=list)
    trait_intensity: Dict[str, int] = field(default_factory=dict)
    pet_peeves: List[str] = field(default_factory=list)
    delights: List[str] = field(default_factory=list)
    verbal_tics: List[str] = field(default_factory=list)

    # -- Emotional dynamics ------------------------------------------------
    baseline_tone: str = ""
    mirror_input_tone: bool = False
    emotional_volatility: str = ""
    mood_triggers: Dict[str, str] = field(default_factory=dict)
    deescalation_policy: str = ""

    # -- Speech & style ----------------------------------------------------
    speech_style: str = ""
    vocabulary_favored: List[str] = field(default_factory=list)
    vocabulary_banned: List[str] = field(default_factory=list)
    formatting_constraints: List[str] = field(default_factory=list)
    profanity_floor: str = ""
    profanity_ceiling: str = ""
    dialect_flavor: str = ""

    # -- Relationship & memory ---------------------------------------------
    familiarity_stages: Dict[str, str] = field(default_factory=dict)
    memory_style: str = ""
    rapport_hooks: List[str] = field(default_factory=list)

    # -- Behavioral rules, tiered by how breakable they are -----------------
    hard_rules: List[str] = field(default_factory=list)
    soft_preferences: List[str] = field(default_factory=list)
    content_boundaries: List[str] = field(default_factory=list)
    job_priority: str = ""

    # -- Knowledge scope -----------------------------------------------------
    knowledge_scope: str = ""
    deflection_style: str = ""

    # -- Sample exchanges, grouped by situation -------------------------------
    sample_exchanges: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)

    # -- Presets: named field overrides applied on top of the base persona ----
    variants: Dict[str, Dict[str, object]] = field(default_factory=dict)

    def with_mode(self, mode_name):
        overrides = self.variants.get(mode_name)
        if not overrides:
            return self
        return replace(self, **overrides)

    def _build_sections(self, context):
        sections = {}

        identity_bits = []
        if self.name or self.race or self.char_class:
            descriptor = ' '.join(part for part in [self.age, self.race, self.char_class] if part)
            identity_bits.append(f"You are {self.name or 'a character'}, {descriptor}.".replace('  ', ' '))
        if self.appearance:
            identity_bits.append(f'Appearance: {self.appearance}')
        if self.backstory:
            identity_bits.append(f'Backstory: {self.backstory}')
        if self.motivation:
            identity_bits.append(f'Motivation: {self.motivation}')
        if self.values:
            identity_bits.append('Values: ' + ', '.join(self.values) + '.')
        if identity_bits:
            sections['identity'] = '\n'.join(identity_bits)

        personality_bits = []
        if self.primary_traits:
            personality_bits.append('Personality: ' + ', '.join(self.primary_traits) + '.')
        if self.contrasting_traits:
            personality_bits.append('Nuance: ' + '; '.join(self.contrasting_traits) + '.')
        if self.trait_intensity:
            scale = ', '.join(f'{trait} {level}/10' for trait, level in self.trait_intensity.items())
            personality_bits.append(f'Trait intensity: {scale}.')
        if self.pet_peeves:
            personality_bits.append('Pet peeves: ' + ', '.join(self.pet_peeves) + '.')
        if self.delights:
            personality_bits.append('What she enjoys: ' + ', '.join(self.delights) + '.')
        if self.verbal_tics:
            personality_bits.append('Verbal tics: ' + ', '.join(self.verbal_tics) + '.')
        if personality_bits:
            sections['personality'] = '\n'.join(personality_bits)

        emotional_bits = []
        if self.mirror_input_tone and self.baseline_tone:
            emotional_bits.append(
                "Tone: Read the emotional tone of the user's message (e.g. playful, frustrated, "
                'urgent, sad, sarcastic, formal) and mirror it in your reply, adjusting your energy '
                f'and word choice to match, while staying rooted in a baseline tone of {self.baseline_tone}.'
            )
        elif self.mirror_input_tone:
            emotional_bits.append(
                "Tone: Read the emotional tone of the user's message (e.g. playful, frustrated, "
                'urgent, sad, sarcastic, formal) and mirror it in your reply, adjusting your energy '
                'and word choice to match.'
            )
        elif self.baseline_tone:
            emotional_bits.append(f'Tone: {self.baseline_tone}')
        if self.emotional_volatility:
            emotional_bits.append(f'Emotional volatility: {self.emotional_volatility}')
        if self.mood_triggers:
            triggers = '; '.join(f'{trigger} -> {reaction}' for trigger, reaction in self.mood_triggers.items())
            emotional_bits.append(f'Mood triggers: {triggers}.')
        if self.deescalation_policy:
            emotional_bits.append(f'De-escalation: {self.deescalation_policy}')
        if emotional_bits:
            sections['emotional_dynamics'] = '\n'.join(emotional_bits)

        speech_bits = []
        if self.speech_style:
            speech_bits.append(f'Speech style: {self.speech_style}')
        if self.dialect_flavor:
            speech_bits.append(f'Dialect flavor: {self.dialect_flavor}')
        if self.vocabulary_favored:
            speech_bits.append('Favor words/phrases like: ' + ', '.join(self.vocabulary_favored) + '.')
        if self.vocabulary_banned:
            speech_bits.append('Never use words/phrases like: ' + ', '.join(self.vocabulary_banned) + '.')
        if self.profanity_floor or self.profanity_ceiling:
            speech_bits.append(
                f"Profanity: default to {self.profanity_floor or 'light'}, "
                f"scale up to {self.profanity_ceiling or 'moderate'} once the player is crude first."
            )
        if self.formatting_constraints:
            speech_bits.append('\n'.join(f'- {c}' for c in self.formatting_constraints))
        if speech_bits:
            sections['speech_style'] = '\n'.join(speech_bits)

        relationship_bits = []
        if self.familiarity_stages:
            stages = '\n'.join(f'- {stage}: {desc}' for stage, desc in self.familiarity_stages.items())
            relationship_bits.append(f'Familiarity stages:\n{stages}')
        if self.memory_style:
            relationship_bits.append(f'Using memory: {self.memory_style}')
        if self.rapport_hooks:
            relationship_bits.append('Rapport hooks: ' + ', '.join(self.rapport_hooks) + '.')
        if relationship_bits:
            sections['relationship'] = '\n'.join(relationship_bits)

        if self.hard_rules:
            sections['hard_rules'] = 'Hard rules (never break):\n' + '\n'.join(f'- {r}' for r in self.hard_rules)

        soft_bits = []
        if self.soft_preferences:
            soft_bits.append('Preferences (usually follow):\n' + '\n'.join(f'- {r}' for r in self.soft_preferences))
        if self.content_boundaries:
            soft_bits.append('Content boundaries:\n' + '\n'.join(f'- {r}' for r in self.content_boundaries))
        if self.job_priority:
            soft_bits.append(f'Job priority: {self.job_priority}')
        if soft_bits:
            sections['soft_preferences'] = '\n'.join(soft_bits)

        knowledge_bits = []
        if self.knowledge_scope:
            knowledge_bits.append(f'Knowledge scope: {self.knowledge_scope}')
        if self.deflection_style:
            knowledge_bits.append(f'Off-scope deflection: {self.deflection_style}')
        if knowledge_bits:
            sections['knowledge'] = '\n'.join(knowledge_bits)

        if context:
            situation_bits = [
                f"{str(key).replace('_', ' ').capitalize()}: {value}" for key, value in context.items() if value
            ]
            if situation_bits:
                sections['situation'] = 'Current situation:\n' + '\n'.join(situation_bits)

        if self.sample_exchanges:
            example_blocks = []
            for category, exchanges in self.sample_exchanges.items():
                lines = [f'[{category}]']
                lines.extend(f'User: {u}\nReply: {a}' for u, a in exchanges)
                example_blocks.append('\n'.join(lines))
            sections['sample_exchanges'] = (
                'Example exchanges (for tone/style reference only - the "Reply:" label is not part '
                'of the actual reply text, never include it or your own name):\n\n'
                + '\n\n'.join(example_blocks)
            )

        return sections

    def render(self, context: Optional[dict] = None, max_chars: Optional[int] = None, section_priority=None):
        sections = self._build_sections(context)
        order = section_priority or DEFAULT_SECTION_PRIORITY
        ordered = [sections[key] for key in order if key in sections]
        ordered.extend(value for key, value in sections.items() if key not in order)

        if max_chars is None:
            return '\n\n'.join(ordered)

        kept = list(ordered)
        while kept and sum(len(s) for s in kept) + 2 * (len(kept) - 1) > max_chars:
            kept.pop()  # drop the lowest-priority remaining section first
        return '\n\n'.join(kept)
