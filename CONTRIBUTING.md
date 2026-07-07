# Contributing to PROTON

Thanks for your interest in PROTON. This is an open-source project, so
contributions are welcome (but may take time for me to review)!

If you have read this far and still have a question, opening an issue is always
a fine way to ask me a question.

## Reporting bugs and suggesting ideas

Bugs and ideas both go on the [issue tracker](https://github.com/DChristensen12/PROTON/issues).

If you are reporting a bug, the things that actually help me reproduce it are:

- your operating system and Python version
- which detector you were using, if any, or whether it was hardware-free
- the exact command you ran and the full error output
- what you expected to happen instead

You do not need hardware to hit or report most bugs, since the library is also built
to run without hardware. More on that below.

## Before you start on something big

For a typo, a small fix, or a doc tweak, just open a pull request, no need to
ask first.

For anything larger, a new feature, a new detector, a change to how a module
works, please open an issue first so we can talk it through before you spend time on it. This is mostly so I do not have to turn away a big pull request
that went in a direction I was not going to take. I would rather sort that out
before you write the code, not after.

## Setting up a development environment

You only need to do this once.

1. Fork the repo on GitHub, then clone your fork:

   ```
   git clone https://github.com/<your-username>/PROTON.git
   cd PROTON
   ```

2. Install it in editable mode so your changes take effect without reinstalling:

   ```
   pip install -e .
   ```

   I develop inside a conda environment, but a plain virtualenv works the same
   way. Nothing about the setup depends on conda.

3. Install pytest so you can run the test suite:

   ```
   pip install pytest
   ```

Now create a branch for your work and you are ready to go:

```
git checkout -b my-change
```

## Running the tests

Run the whole suite from the repo root:

```
pytest
```

The tests do not need any hardware. Every detector has a hardware-free twin and
the tests drive those instead of a real device, using fake serial ports and fake
detector objects. So you can develop and verify almost everything on a machine
with nothing plugged into it.

If you add code, add tests for it, and follow the existing pattern of testing
against the fake devices rather than assuming a detector is connected.

## Coding style

PROTON has a specific comment style and I prefer this style for consistency, so it is worth reading this before you write code.

- Put a triple-quoted docstring under every new class and every new function and explain what it is supposed to do.
- For a note about a single line, put a short `#` comment inline on that line.
- For a note that spans several lines, put the `#` comment directly above them.
- Keep comments short and sparse. A few brief notes where they genuinely help,
  not a wall of explanation over every block.

I am fine with other commenting styles, as long as it is clear what the code is doing!

## Project layout

The core code lives in the `proton/` package. The parts you are most likely to
touch:

| Path | What is there |
|------|---------------|
| `proton/Hardware/Detectors/` | One subpackage per detector, each with a readout module, check and record scripts, and tests |
| `proton/common/` | Shared code used across detectors, like the recording helper |
| `proton/default_data/` | Bundled reference data captured from real hardware |

Each detector subpackage follows the same shape. There is a class that works
with the real device, and a hardware-free twin next to it that replays or
synthesizes data. There are check_*.py and record_*.py scripts for bench
use. Tests run against the digital twin, not the real device. If you are
adding support for a new, specific type of detector, follow that pattern and
the rest of the library will slot around it.

## Commits and pull requests

Write commit messages that describe what the commit actually does.

When your branch is ready, push it to your fork and open a pull request against
`main`. In the pull request description, say what you changed and why, and if it
closes an issue, include `Fixes #N` so the two get linked.

## Using code from other sources

If you bring in code from somewhere else, be explicit about where it came from
and what license it was released under. The simplest safe thing is to copy the
original license text into the header of the file you added it to. PROTON is
released under the BSD 3-Clause license, so anything you contribute needs to be
compatible with that.

## Documentation

For now the docstrings are the documentation, so if you change how something
behaves, update its docstring in the same change. The README covers the higher
level picture of what PROTON is and where it is going. The docs/ folder goes
deeper on specific parts. Right now that means ARCHITECTURE.md, for how the
project fits together, and HARDWARE.md, for the detectors themselves. More
documents will probably join them as the modeling side of the project grows.
If a change affects any of these, update them alongside the code. If you spot
a typo or an awkward sentence anywhere, a fix for that is a perfectly good
contribution too.