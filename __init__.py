# -*- coding: utf-8 -*-

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name

    from .gazetteer_bb import GazetteerBB

    return GazetteerBB(iface)
