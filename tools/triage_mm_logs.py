import re, sys, collections, json
pat_err = re.compile(r"MM Bot error: (.+)")
pat_skip = re.compile(r"\[SKIP\]\s+(.*)")
pat_error = re.compile(r"ERROR.*?:(.+)")
pat_warn = re.compile(r"WARNING.*?:(.+)")
pat_fail = re.compile(r"Failed.*?:(.+)")
ctr = collections.Counter()
with open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m1 = pat_err.search(line)
        if m1: ctr[f"error:{m1.group(1).strip()}"] += 1
        m2 = pat_skip.search(line)
        if m2: ctr[f"skip:{m2.group(1).strip()}"] += 1
        m3 = pat_error.search(line)
        if m3: ctr[f"error_general:{m3.group(1).strip()}"] += 1
        m4 = pat_warn.search(line)
        if m4: ctr[f"warning:{m4.group(1).strip()}"] += 1
        m5 = pat_fail.search(line)
        if m5: ctr[f"failed:{m5.group(1).strip()}"] += 1
print(json.dumps(ctr.most_common(), indent=2))
