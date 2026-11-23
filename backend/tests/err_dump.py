"""Print the tail of the backend error log to find the latest exception."""

import re

content = open("backend\\uvicorn.err").read()
print("file length:", len(content))
print("----- last 3500 chars -----")
print(content[-3500:])
