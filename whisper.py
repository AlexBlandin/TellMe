from collections import Counter as bag
with open("whisper.txt","r") as o:
  b=bag(o.read().replace("\n"," ").replace(".","").replace(",","").replace("?","").lower().split())
  for dud in "the in as have an no with who could couldn't on that he he's so his but got for out you to has and had was is a of them their all some there are they this it went said were i be been what not".split():
    if dud in b: del b[dud]
  for k in list(b.keys()):
    if k+"s" in b:
      b[k] += b[k+"s"]
      del b[k+"s"]
    if k+"'s" in b:
      b[k] += b[k+"'s"]
      del b[k+"'s"]
  s={k:b[k] for k in sorted(b.keys(), key=lambda k:b[k], reverse=True)[:10] if b[k]>1}
  for k,v in s.items(): print(k, v)
