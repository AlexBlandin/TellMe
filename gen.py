from pathlib import Path
from subprocess import run

from gtts import gTTS

fl = Path("./audio/pre/")
fl.mkdir(exist_ok=True)

a = [
  "Welcome to TellMe!",
  "I shall begin shortly!",
  "Your time is up.",
  "Momentarily, you will be moved back to the lobby, and invited to vote for the next player's prompts. The voting channel will soon appear for you.",
  "The round has ended, so you will be moved back to the lobby shortly.",
  "The round has concluded.",
  "I hope you enjoyed playing Tell Me. Please wait a moment while I prepare the session recording.",
  "Thank you for playing Tell Me, attached is the combined session recording.",
]
al = len(a)
a = [(s, "-".join("".join(filter(str.isalpha, word)) for word in s.lower().split()[:4])) for s in a]
assert al == len(a)
for s, n in a:
  f = fl / f"{n}.wav"
  m = fl / f"{n}.mp3"
  gTTS(s).save(str(m))
  run(["ffmpeg", "-loglevel", "panic", "-i", str(m), str(f)], check=False)
  print(str(f), repr(s))

for f in fl.glob("*"):
  print(str(f))
