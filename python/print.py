from datetime import datetime

PROGRESS_BAR_LENGTH = 20

def _block_display(v: float, length: int):
    table = ['\u2003', '\u258f', '\u258e', '\u258d', '\u258c', '\u258b', '\u258a', '\u2589', '\u2588']
    blocks_float = length * v
    blocks_int = int(blocks_float)
    last_block = int((blocks_float - blocks_int) * 8)
    progress_bar = '\u2588' * blocks_int
    if last_block != 0:
        progress_bar += table[last_block]
    progress_bar += (length - len(progress_bar)) * table[0]
    return progress_bar + table[1]


def progress_bar(title: str, val: float):
    print(title.ljust(20), _block_display(val, PROGRESS_BAR_LENGTH), end='\n\033[A')


def progress_bar_end(title: str):
    print(title.ljust(20), _block_display(1, PROGRESS_BAR_LENGTH), end='\n\033[A\n')


def I(comp: str, *args, **kargs):
    _print('I', comp, *args, **kargs)


def E(comp: str, *args, **kargs):
    _print('E', comp, *args, **kargs)


def W(comp: str, *args, **kargs):
    _print('W', comp, *args, **kargs)


def _print(t: str, comp: str, *args, **kargs):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t, '[' + comp.ljust(5) + ']', *args, **kargs)
