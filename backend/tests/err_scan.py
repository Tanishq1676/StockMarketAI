"""Find the fresh 500 error for POST /api/reports/hourly."""

import re

content = open("backend\\uvicorn.err").read()
starts = [m.start() for m in re.finditer(r"Traceback", content)]
print("num tracebacks:", len(starts))
if starts:
    last = starts[-1]
    chunk = content[last:last + 6000]
    errs = re.findall(r"\b(Error|Exception)[^\n]*", chunk)
    print("ERR:", errs[-1] if errs else "none")
    frames = re.findall(r"File \"C:\\Users\\ASUS\\OneDrive[^\n]*", chunk)
    for f in frames[-5:]:
        print("  ", f[:140])
    print("---- routes frames ----")
    for f in re.findall(r"File \"C:\\Users\\ASUS\\OneDrive\\Documents\\Default Project\\backend\\app\\routes\\[^\n]*", chunk):
        print("  ", f[:140])
    for f in re.findall(r"File \"C:\\Users\\ASUSAi\\Documents[^\n]*", chunk):
        print("  (alts)", f[:140])
    for f in re.findall(r"File \"C:\\Users\\ASUSE\\Documents[^\n]*", chunk):
        print("  (alts2)", f[:140])
