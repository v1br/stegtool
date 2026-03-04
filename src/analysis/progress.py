import sys


def print_progress(current, total):

    bar_len = 30
    progress = current/total

    filled = int(bar_len*progress)

    bar = "#"*filled + "-"*(bar_len-filled)

    sys.stdout.write(f"\r[{bar}] {current}/{total}")
    sys.stdout.flush()