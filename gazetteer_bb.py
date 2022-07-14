# -*- coding: utf-8 -*-
"""
/***************************************************************************
                          Gazetteer Berlin/Brandenburg
                              -------------------
        begin                : 2021-10-25
        copyright            : (C) 2021 by Marcus Mohr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import json
import os.path
from tokenize import group

from qgis.core import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtNetwork import QNetworkRequest
from .collapsible_box import CollapsibleBox
from .gazetteer_bb_dockwidget import GazetteerBBDockWidget
from .item_data import ItemData
from .resources import *
from .result_item_widget import ResultItemWidget
from urllib.parse import urlencode

log_header = 'Gazetteer Berlin/Brandenburg'

class GazetteerBB:
    """Main code."""


    def __init__(self, iface):
        """Constructor with an interface (iface) which provides the
        hook by which you can extend QGIS.
        """

        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        self.locale = QSettings().value('locale/userLocale')[0:2]

        # Make sure english translation is loaded if lang is not german
        if self.locale != 'de':
            self.locale = 'en'
            locale_path = os.path.join(
                self.plugin_dir,
                'i18n',
                'gazetteer_bb_en.qm')

            if os.path.exists(locale_path):
                self.translator = QTranslator()
                self.translator.load(locale_path)
                QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr(u'&Gazetteer Berlin/Brandenburg')

        self.toolbar = self.iface.addToolBar(u'Gazetteer Berlin/Brandenburg')
        self.toolbar.setObjectName(u'GazetteerBB')

        self.pluginIsActive = False
        self.dockwidget = None

        self.current_page = 1
        self.limit = 20
        self.url = 'https://search.geobasis-bb.de'
        self.layer = True
        self.geometry = True
        self.fill_color = QColor(52, 84, 152, 50)
        self.border_color = QColor(0, 0, 0)
        self.fill_color_point = QColor(220, 20, 30, 200)
        self.border_color_point = QColor(0, 0, 0)


    # noinspection PyMethodMayBeStatic
    def tr(self, message) -> str:
        """Get the translation for a string using Qt translation API."""

        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GazetteerBB', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None) -> QAction:
        """Add a toolbar icon to the toolbar."""

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/qgs-gazetteer-bb/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Gazetteer Berlin/Brandenburg'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        self.dockwidget.searchEdit.clear()
        self.dockwidget.resultWidget.clear()
        self.dockwidget.pageLabel.clear()
        self.dockwidget.hitsLabel.clear()

        self.clear_opt_filter(self.dockwidget.filterBoxLayout)

        self.pluginIsActive = False


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Gazetteer Berlin/Brandenburg'),
                action)
            self.iface.removeToolBarIcon(action)

        del self.toolbar


    def run(self):
        """Loads and starts the plugin."""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget is None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = GazetteerBBDockWidget()
                self.connect_ui()
                self.set_tooltips()

            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)

            self.load_default_settings(True)
            self.load_settings()

            self.dockwidget.backButton.setVisible(False)
            self.dockwidget.nextButton.setVisible(False)
            self.dockwidget.confirmButton.setVisible(False)

            self.timer = QTimer()
            self.timer.timeout.connect(self.hide_settings_label)

            self.dockwidget.hintLabel.setVisible(True)

            self.dockwidget.show()


    def connect_ui(self):
        """Connect ui elements with functions."""

        self.dockwidget.addressBox.clicked.connect \
            (lambda: self.update_search(True))
        self.dockwidget.backButton.clicked.connect \
            (lambda: self.update_search(True, -1))
        self.dockwidget.cadastreBox.clicked.connect \
            (lambda: self.update_search(True))
        self.dockwidget.confirmButton.clicked.connect \
            (self.confirm_opt_filter)
        self.dockwidget.complexBox.clicked.connect \
            (lambda: self.update_search(True))
        self.dockwidget.transportBox.clicked.connect \
            (lambda: self.update_search(True))
        self.dockwidget.nextButton.clicked.connect \
            (lambda: self.update_search(True, 1))
        self.dockwidget.resetButton.clicked.connect \
            (lambda: self.load_default_settings(False))
        self.dockwidget.saveButton.clicked.connect \
            (self.store_settings)
        self.dockwidget.searchButton.clicked.connect \
            (lambda: self.update_search(False))
        self.dockwidget.resultWidget.itemSelectionChanged.connect \
            (self.add_vlayer)
        self.dockwidget.searchEdit.returnPressed.connect \
            (self.dockwidget.searchButton.click)
        self.dockwidget.closingPlugin.connect \
            (self.onClosePlugin)


    def set_tooltips(self):
        if self.locale == 'de':
            self.dockwidget.addressBox.setToolTip \
                ('Adressen und Orte durchsuchen')
            self.dockwidget.cadastreBox.setToolTip \
                ('Katasterdaten durchsuchen')
            self.dockwidget.complexBox.setToolTip \
                ('Statt einer Bounding Box wird die wahre Geometrie zur Karte hinzugefügt (wenn verfügbar)')
            self.dockwidget.layerBox.setToolTip \
                ('Beim Klick auf ein Ergebnis wird die Geometrie in der Karte angezeigt und als Layer dem Themenbaum hinzugefügt')
            self.dockwidget.transportBox.setToolTip \
                ('Haltestellen durchsuchen')
            self.dockwidget.saveButton.setToolTip \
                ('Speichert die Einstellungen im Nutzerprofil')
            self.dockwidget.resetButton.setToolTip \
                ('Stellt die Standardeinstellungen wieder her')
        else:
            self.dockwidget.addressBox.setToolTip \
                ('Search addresses and places')
            self.dockwidget.cadastreBox.setToolTip \
                ('Search cadastral data')
            self.dockwidget.complexBox.setToolTip \
                ('True geometry is added to the map instead of a bounding box (if available)')
            self.dockwidget.layerBox.setToolTip \
                ('When you click on a result, the geometry is displayed on the map and added to the layer tree')
            self.dockwidget.transportBox.setToolTip \
                ('Search transport stops')
            self.dockwidget.saveButton.setToolTip \
                ('Saves the settings in the user profile')
            self.dockwidget.resetButton.setToolTip \
                ('Restores the default settings')


    def update_search(self, opt_filter, status=0):
        """Starting point for every search."""

        self.dockwidget.resultWidget.clear()

        if status == 0:
            self.current_page = 1
        else:
            self.current_page = self.current_page + status

        term = self.dockwidget.searchEdit.text()

        if term != '':
            param = self.get_query(term, opt_filter)
            json_response = self.query_search(param)
            self.on_finish_query(json_response, opt_filter)


    def get_query(self, term, opt_filter) -> dict:
        """Builds and returns querystring depending on user settings."""

        start = 0
        limit = int(self.dockwidget.resultsBox.text())

        complex_geom = self.dockwidget.complexBox.isChecked()
        categories = self.get_categories_filter()

        if self.current_page != 1:
            start = (self.current_page - 1) * limit

        param = {'query': term, 'complex': complex_geom, 'start': start, \
            'limit': limit, 'filter[category]': categories, 'lang': self.locale}

        if opt_filter:
            for key in self.filter_widgets:
                value = ''
                if self.filter_widgets[key].selectedItems():
                    for item in self.filter_widgets[key].selectedItems():
                        value += str(item.data(QtCore.Qt.UserRole)) + '|'
                    filter_key = 'filter[' + key + ']'
                    param[filter_key] = value[:-1]

        return param


    def get_categories_filter(self) -> str:
        """Returns category filter of search api which is chosen by user."""

        categories = ''
        address = self.dockwidget.addressBox
        cadastre = self.dockwidget.cadastreBox
        transport = self.dockwidget.transportBox

        if address.isChecked():
            categories = categories + '|' + 'gazetteer'
        
        if cadastre.isChecked():
            categories = categories + '|' + 'kataster'

        if transport.isChecked():
            categories = categories + '|' + 'haltestellen'

        if address.isChecked() is False and cadastre.isChecked() is False \
            and transport.isChecked() is False:
                categories = 'gazetteer|kataster'
                address.setChecked(True)
                cadastre.setChecked(True)

        return categories


    def query_search(self, param) -> str:
        """Blocking request to search api with qgs function to support
           user specific network settings (e.g. proxy).
        """

        base_url = self.dockwidget.urlEdit.text()
        query = base_url + '/search/?' + urlencode(param)

        self.log_info(str(query))

        qrequest = QgsBlockingNetworkRequest()
        netrequest = QNetworkRequest(QUrl(query))

        err = qrequest.get(netrequest, True)

        if err == 0:
            output = qrequest.reply().content().data().decode('utf-8')
        else:
            output = None
            self.log_info(str('Network error. Please see Network tab.'))
            self.openLog()

        return output


    def on_finish_query(self, json_response, opt_filter):
        """Called after sucessful query to manipulate UI."""

        data = json.loads(json_response)

        if json_response is not None:
            if opt_filter is False:
                self.update_opt_filter(data)

            self.update_results(data)
            self.update_paging(data)


    def update_opt_filter(self, data):
        """Dynamically updated filter depending on
           result of search api.
        """

        filter_layout = self.dockwidget.filterBoxLayout
        self.clear_opt_filter(filter_layout)

        self.dockwidget.confirmButton.setVisible(True)
        self.dockwidget.hintLabel.setVisible(False)

        self.filter_widgets = {}

        for i in data['stats']:
            if i['vals'] and i['attribute'] != 'category':
                box = CollapsibleBox(i['label'])
                filter_layout.addWidget(box)
                widget_layout = QVBoxLayout()

                widget = QListWidget()
                widget.setSelectionMode(2)

                for u in i['vals']:
                    item = QListWidgetItem()
                    if 'label' in u:
                        item.setText(u['label'])
                    else:
                        item.setText(u['value'])

                    item.setData(QtCore.Qt.UserRole, u['value'])
                    widget.addItem(item)

                widget_layout.addWidget(widget)
                box.set_layout(widget_layout)
                self.filter_widgets[i['attribute']] = widget


    def clear_opt_filter(self, layout):
        """Filter differ depending on result set. Therefore 
           they have to be removed with every new search.
        """

        for i in reversed(range(layout.count())): 
            layout.itemAt(i).widget().deleteLater()


    def confirm_opt_filter(self):
        """Update search and jump to results after
           confirming the filter.
        """

        self.update_search(True)
        self.dockwidget.tabWidget.setCurrentIndex(0)


    def update_results(self, data):
        """Add items to result list. Complex geometry (not bbox) 
           is only available in response if user sets the filter. 
        """

        epsg = data['geo_system']

        for i in data['results']:

            item = QListWidgetItem()
            item_data = ItemData(i['id'])
            item_data.title = i['title']
            item_data.subtitle = None
            item_data.epsg = epsg
            item_data.type = self.get_type_label(data, i['type'])

            if 'geometryComplex' in i:
                item_data.geom = i['geometryComplex']
            else:
                item_data.geom = i['geometry']

            item_data.geom_type = item_data.geom.split('(')[0]

            if 'subtitle' in i['additionalData']:
                item_data.subtitle = i['additionalData']['subtitle']

            if item_data.subtitle is None:
                resultItemWidget = ResultItemWidget(item_data.title, item_data.type)
            else:
                combined_header = item_data.type + ' | ' + item_data.subtitle
                resultItemWidget = ResultItemWidget(item_data.title, combined_header)

            item.setData(QtCore.Qt.UserRole, item_data)
            item.setSizeHint(resultItemWidget.sizeHint())

            self.dockwidget.resultWidget.addItem(item)
            self.dockwidget.resultWidget.setItemWidget(item, resultItemWidget)


    def get_type_label(self, data, type) -> str:
        """This matches the type for each result with the values
           of the stats to determine a user friendly label.
        """

        for i in data['stats']:
            if i['vals'] and i['attribute'] == 'type':
                for u in i['vals']:
                    if type == u['value']:
                        type_label = u['label']

        return type_label


    def update_paging(self, data):
        """Set UI elements for paging to improve handling
           of thousand of results.
        """

        hits = data['total']
        start = data['from']
        limit = int(self.dockwidget.resultsBox.value())

        if self.current_page == 1:
            self.dockwidget.backButton.setVisible(False)
        else:
            self.dockwidget.backButton.setVisible(True)

        if hits > start + limit:
            self.dockwidget.nextButton.setVisible(True)
        else:
            self.dockwidget.nextButton.setVisible(False)

        if self.locale == 'de':
            self.dockwidget.pageLabel.setText('Seite ' + str(self.current_page))
        else:
            self.dockwidget.pageLabel.setText('Page ' + str(self.current_page))

        self.dockwidget.hitsLabel.setText(str(start + 1) + ' - ' + \
            str(start + limit) + ' / ' + str(hits))


    def add_vlayer(self):
        """Called when user clicks on result item. Create
           vector layer and add it on the map.
        """

        group_name = 'Gazetteer BE/BB'
        group_layer = self.find_group(group_name)
        if not group_layer:
            QgsProject.instance().layerTreeRoot().addGroup(group_name)
            group_layer = self.find_group(group_name)

        items = self.dockwidget.resultWidget.selectedItems()

        if items:
            item_data = items[0].data(QtCore.Qt.UserRole)
            layer_name = item_data.title
            layer = self.create_layer(item_data.geom, item_data.geom_type, layer_name)

            self.set_map_extent(layer, item_data.geom_type)

            create_layer = self.dockwidget.layerBox.isChecked()

            if create_layer:
                QgsProject.instance().addMapLayers([layer], False)
                group_layer.addLayer(layer)


    def find_group(self, group_name) -> QgsLayerTreeGroup:
        group_layer = QgsProject.instance().layerTreeRoot().findGroup(group_name)
    
        return group_layer


    def create_layer(self, geom, geom_type, name) -> QgsVectorLayer:
        """Set UI elements for paging to improve handling
           of results.
        """

        type_str = geom_type + '?crs=epsg:4326'

        layer = QgsVectorLayer(type_str, name, 'memory')

        provider = layer.dataProvider()

        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt(geom))
        provider.addFeatures([feature])

        symbol = self.get_layer_symbol(geom_type)
        layer.renderer().setSymbol(symbol)

        layer.updateExtents()

        return layer


    def get_layer_symbol(self, geom_type) -> QgsFillSymbol:
        """Different symbols have to be created depending on
           geometry of each result item.
        """

        style = None
        fill_color = self.dockwidget.fillColorButton.color().name(1)
        border_color = self.dockwidget.borderColorButton.color().name(1)
        properties = {'color': fill_color, 'outline_color': border_color}

        fill_color_point = self.dockwidget.fillColorPointButton.color().name(1)
        border_color_point = self.dockwidget.borderColorPointButton.color().name(1)
        properties_point = {'color': fill_color_point, 'outline_color': border_color_point, 'size': '3'}

        if geom_type.lower() == 'point':
            style = QgsMarkerSymbol.createSimple(properties_point)
        elif geom_type.lower() == 'multipoint':
            style = QgsMarkerSymbol.createSimple(properties_point)
        elif geom_type.lower() == 'line':
            style = QgsLineSymbol.createSimple(properties)
        elif geom_type.lower() == 'multiline':
            style = QgsLineSymbol.createSimple(properties)
        elif geom_type.lower() == 'polygon':
            style = QgsFillSymbol.createSimple(properties)
        elif geom_type.lower() == 'multipolygon':
            style = QgsFillSymbol.createSimple(properties)
        else:
            self.log_error('Geometry type <' + geom_type + '> not supported')
            self.openLog()

        return style


    def set_map_extent(self, layer, geom_type):
        """Move map to selected result geometry."""

        canvas = self.iface.mapCanvas()

        src_crs = layer.crs()
        qcrs_source = QgsCoordinateReferenceSystem(src_crs)

        dest_crs = canvas.mapSettings().destinationCrs().authid()
        qcrs_dest = QgsCoordinateReferenceSystem(dest_crs)

        qct = QgsCoordinateTransform(qcrs_source, qcrs_dest, QgsProject.instance())

        canvas.setExtent(qct.transform(layer.extent()))

        if geom_type.lower() == 'point':
            canvas.zoomScale(5000)

        canvas.refresh()


    def store_settings(self):
        """User can edit and store different settings."""

        settings = QgsSettings()

        url = self.dockwidget.urlEdit.text()
        results = self.dockwidget.resultsBox.value()
        layer = self.dockwidget.layerBox.isChecked()
        complex_geom = self.dockwidget.complexBox.isChecked()
        fill_color = self.dockwidget.fillColorButton.color()
        fill_color_point = self.dockwidget.fillColorPointButton.color()
        border_color = self.dockwidget.borderColorButton.color()
        border_color_point = self.dockwidget.borderColorPointButton.color()

        settings.setValue("gazetteerBB/url", url)
        settings.setValue("gazetteerBB/results",  results)
        settings.setValue("gazetteerBB/layer", layer)
        settings.setValue("gazetteerBB/geometry", complex_geom)
        settings.setValue("gazetteerBB/fill_color", fill_color)
        settings.setValue("gazetteerBB/fill_color_point", fill_color_point)
        settings.setValue("gazetteerBB/border_color", border_color)
        settings.setValue("gazetteerBB/border_color_point", border_color_point)

        if self.locale == 'de':
            self.set_settings_label('Die Werte wurden erfolgreich gespeichert! '
                + 'Die neuen Einstellungen werden bei der nächsten Suche berücksichtigt.')
        else:
            self.set_settings_label('The values ​​were saved successfully! The new settings '
                + 'will take effect on next search.')


    def load_settings(self):
        """Load user specific settings at start up."""

        settings = QgsSettings()

        url = settings.value("gazetteerBB/url")
        results = settings.value("gazetteerBB/results")
        layer = settings.value("gazetteerBB/layer")
        complex_geom = settings.value("gazetteerBB/geometry")
        fill_color = settings.value("gazetteerBB/fill_color")
        fill_color_point = settings.value("gazetteerBB/fill_color_point")
        border_color = settings.value("gazetteerBB/border_color")
        border_color_point = settings.value("gazetteerBB/border_color_point")

        if url is not None:
            self.dockwidget.urlEdit.setText(url)

        if results is not None:
            self.dockwidget.resultsBox.setValue(int(results))

        if layer is not None:
            self.dockwidget.layerBox.setChecked(bool(layer))

        if complex_geom is not None:
            self.dockwidget.complexBox.setChecked(bool(complex_geom))

        if fill_color is not None:
            self.dockwidget.fillColorButton.setColor(fill_color)

        if fill_color_point is not None:
            self.dockwidget.fillColorPointButton.setColor(fill_color_point)

        if border_color is not None:
            self.dockwidget.borderColorButton.setColor(border_color)

        if border_color_point is not None:
            self.dockwidget.borderColorPointButton.setColor(border_color_point)


    def load_default_settings(self, start):
        self.dockwidget.urlEdit.setText(self.url)
        self.dockwidget.resultsBox.setValue(self.limit)
        self.dockwidget.layerBox.setChecked(self.layer)
        self.dockwidget.complexBox.setChecked(self.geometry)

        fill_color = self.fill_color
        fill_color_point = self.fill_color_point
        border_color = self.border_color
        border_color_point = self.border_color_point

        self.dockwidget.fillColorButton.setColor(fill_color)
        self.dockwidget.fillColorPointButton.setColor(fill_color_point)
        self.dockwidget.borderColorButton.setColor(border_color)
        self.dockwidget.borderColorPointButton.setColor(border_color_point)

        if start is False:
            if self.locale == 'de':
                self.set_settings_label('Die Werte wurden zurückgesetzt! Die neuen '
                    + 'Einstellungen werden bei der nächsten Suche berücksichtigt.')
            else:
                self.set_settings_label('The values have been reset! The new '
                    + 'settings will take effect on next search.')


    def set_settings_label(self, text):
        """Help text to let user know that settings
           were stored or default settings are loaded.
        """

        self.dockwidget.settingsLabel.setText(text)
        self.dockwidget.settingsLabel.setVisible(True)
        self.timer.start(5000)


    def hide_settings_label(self):
        self.dockwidget.settingsLabel.setVisible(False)


    def log_info(self, msg):
        QgsMessageLog.logMessage(msg, log_header, Qgis.Info)


    def log_warning(self, msg):
        QgsMessageLog.logMessage(msg, log_header, Qgis.Warning)


    def log_error(self, msg):
        QgsMessageLog.logMessage(msg, log_header, Qgis.Critical)


    def openLog(self):
        self.iface.mainWindow().findChild(QDockWidget, 'MessageLog').show()
