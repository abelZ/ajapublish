from flask import g


class PortObj:
    def __init__(self):
        self.port = {}


def get_port():
    if 'po' not in g:
        print('po not in g')
        g.po = PortObj()

    return g.po
