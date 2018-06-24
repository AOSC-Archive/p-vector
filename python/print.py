from datetime import datetime


def I(comp: str, *args):
    _print('I', comp, *args)


def E(comp: str, *args):
    _print('E', comp, *args)


def _print(t: str, comp: str, *args):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          t, '[' + comp + ']', *args)
