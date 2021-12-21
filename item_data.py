class ItemData:
    """Simple class for search result items
       with all necessary properties.
    """

    def __init__(self, id):
        self._id = id


    @property
    def id(self):
        return self._id


    @property
    def type(self):
        return self._type


    @property
    def title(self):
        return self._title


    @property
    def subtitle(self):
        return self._subtitle


    @property
    def geom(self):
        return self._geom


    @property
    def epsg(self):
        return self._geom


    @id.setter
    def id(self, id):
        self._id = id


    @type.setter
    def type(self, type):
        self._type = type


    @title.setter
    def title(self, title):
        self._title = title


    @subtitle.setter
    def subtitle(self, subtitle):
        self._subtitle = subtitle


    @geom.setter
    def geom(self, geom):
        self._geom = geom


    @epsg.setter
    def epsg(self, epsg):
        self._epsg = epsg
