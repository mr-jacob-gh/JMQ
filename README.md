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


## Druid Block Spells
/blockspell add me 2424 553 1440 551 2429 556 1438 2419 1434 550 554 558 555
/blockspell add me 557 2020 552 1398 1517 2199 2198 1736 1737 1736 1737 1738 1739


/blockspell remove me 2424 553 1440 551 2429 556 1438 2419 1434 550 554 558 555
/blockspell remove me 557 2020 552 1398 1517 2199 2198 1736 1737 1736 1737 1738 1739

## TODO
