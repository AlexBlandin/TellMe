# TellME
> Voice-Assistant based Improv + Chinese-Whispers concept

Example session recording based on the `basic` ruleset provided.

## Installation

Ensure [Python >=3.8,<3.10](https://python.org/) is installed.

Install [Poetry](https://python-poetry.org/), open the `$ poetry shell` in the project directory (it handles `venv` etc.), and use `$ poetry install`. This should handle everything using the supplied `poetry.lock` file; if you wish to update the dependencies use `$ poetry update`.

Install [`libopus0`](https://packages.debian.org/buster/libopus0)/[`libopus`](https://opus-codec.org) (depending on system) and [`ffmpeg`](https://ffmpeg.org/).

Have a `token.txt` file available that has your Discord Bot token, and an `owner.txt` file with your Discord User ID.

Naturally, the bot needs to be invited to the server. Currently, these are the expected permissions (321976400):

![](./permissions.png)

## Running

While in the poetry shell, use `$ poetry run python3 tellme.py`

The bot is online and, if connected to your server, will login. Type `!play` when all players are in voice-chat with you and the game will commence. (TEMP: Assumes roles and channel names, a todo is to have the bot perform all setup)

***

### Citing TellMe

```bib
@misc{
  author={Ibrahim Al-Jeffery, Alex Blandin, Adam Cook, Ibukun Olatunji, Simon Robinson},
  title={{TellMe -- Voice-Assistant based Improv}},
  url = {https://github.com/AlexBlandin/TellMe},
  howpublished = {{available} at \url{https://github.com/AlexBlandin/TellMe}}
}
```

***

### Style-guide for pull requests

We have included `yapf` styling in the `pyproject.toml`, so autoformat with that before contributing. In essense, it's PEP8 with 120 columns. Also, some rules of thumb for strings:
- Prefer `"` over `'`, such as `"hello, world"`
- f-strings `f"` are preferred over `.format()`, do not use `"" % x`
  - `'` are accepted in f-strings to aid nesting (`f"hello {plural('world')}"`)
