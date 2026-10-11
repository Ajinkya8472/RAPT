from detector import detect
from samples import sample_prompt
from scoring import ladder, h

for s in detect(sample_prompt()):
    s.level = 0
    print(s.type, "| level", s.level, "| h =", repr(h(s)), "| ladder =", ladder(s))