# JMQ
EQ Spell Casting Bot

## Requirements

```
pip install pydirectinput
```

## Project Structure

```
src/jmq/
├── config.py        # Static data: file paths, spells, spell IDs, phrase map
├── state.py         # Runtime state: queue, roster, stats, memorized spells
├── utils.py         # Logging and stats helpers
├── actions.py       # Game input: keystrokes, tells, sit/stand, roster update
├── spells.py        # Spell memorization, casting, and spell request handling
├── log_monitor.py   # EQ log file tail and event parsing
├── queue_manager.py # Task queue processing
└── main.py          # Entry point and keep-alive loop
```

## Configuration

Before running, verify the paths in `src/jmq/config.py` match your EverQuest installation:

```python
log_filepath = "C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/Logs/eqlog_Zlem_fangbreaker.txt"
roster_filepath = "C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/"
log_file_path = "jmq.log"
```

## Running the Bot

From the `src/` directory:

```
cd src
python -m jmq.main
```

Make EverQuest the active window within 10 seconds of starting. The bot will:
1. Stand, sit, and load default spells (luclin)
2. Pull the current guild roster
3. Begin monitoring the EQ log for spell requests via tells


## TODO
- /disband before inviting for group spells - done
- account for fizzles
  - Your XXX spell fizzles!
- account for players zoning prematurely
  - You must first select a target for this spell!
  - I don't see anyone by that name around here...
- notify players when they are too low lvl for a spell
  - Your spell is too powerful for your intended target.
- track player request stats