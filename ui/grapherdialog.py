from functools import partial
import os
from typing import List, Set
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget
    )


class GrapherDialog(QDialog):
    
    AREA_HEIGHT  = 400
    BUTTON_WIDTH =  30
    FIELD_WIDTH  = 400
    LABEL_WIDTH  =  80
    ROW_HEIGHT   =  25
    
    filters = {'boundaries': 'GeoJSON (*.geojson)',
               'contours'  : 'GeoTIFF (*.tif)',
               'maps'      : 'OpenStreetMap (*.osm)',
               'places'    : 'Comma Separated Value (*.csv)'}
    
    extensions = {'boundaries': '.geojson',
                  'contours'  : '.tif',
                  'maps'      : '.osm',
                  'places'    : '.csv'}
    
    def __init__(self, existing_boundaries: Set[str] = set(),
                 existing_contours: Set[str] = set(),
                 existing_maps: Set[str] = set(),
                 existing_places: Set[int] = set()):
        super().__init__()
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setWindowTitle('gistools — grapher')
        
        self.existing = {
            'boundaries': existing_boundaries,
            'contours'  : existing_contours,
            'maps'      : existing_maps,
            'places'    : existing_places
            }
        
        self.labels = {
            'boundaries_source' : QLabel('Source Type'),
            'boundaries_path'   : QLabel('Path'),
            'boundaries_enforce': QLabel('Enforce'),
            'contours_source'   : QLabel('Source Type'),
            'contours_path'     : QLabel('Path'),
            'contours_interval' : QLabel('Interval'),
            'maps_source'       : QLabel('Source Type'),
            'maps_path'         : QLabel('Path'),
            'places_source'     : QLabel('Source Type'),
            'places_path'       : QLabel('Path')
            }
        for label in self.labels.values():
            label.setFixedWidth(self.LABEL_WIDTH)
        
        self.fields = {
            'boundaries_path' : QLineEdit(),
            'contours_path'   : QLineEdit(),
            'contour_interval': QSpinBox(),
            'maps_path'       : QLineEdit(),
            'places_path'     : QLineEdit()
            }
        for field in self.fields.values():
            if isinstance(field, QLineEdit):
                field.setClearButtonEnabled(True)
            field.setMinimumWidth(self.FIELD_WIDTH)
        
        self.buttons = {
            'boundaries_folder' : QRadioButton('Directory'),
            'boundaries_file'   : QRadioButton('File (.geojson)'),
            'browse_boundaries' : QPushButton('...'),
            'enforce_boundaries': QCheckBox(),
            'contours_folder'   : QRadioButton('Directory'),
            'contours_file'     : QRadioButton('File (.tif)'),
            'browse_contours'   : QPushButton('...'),
            'maps_folder'       : QRadioButton('Directory'),
            'maps_file'         : QRadioButton('File (.osm)'),
            'browse_maps'       : QPushButton('...'),
            'places_folder'     : QRadioButton('Directory'),
            'places_file'       : QRadioButton('File (.csv)'),
            'browse_places'     : QPushButton('...')
            }
        
        self.tables = {
            'boundaries': QTableWidget(0, 1),
            'contours'  : QTableWidget(0, 1),
            'maps'      : QTableWidget(0, 1),
            'places'    : QTableWidget(0, 1)
            }
        for table in self.tables.values():
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            table.horizontalHeader().setVisible(False)
            table.verticalHeader().setDefaultSectionSize(self.ROW_HEIGHT)
            table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            table.verticalHeader().setVisible(False)
            table.setGridStyle(Qt.NoPen)
            table.setMinimumHeight(self.AREA_HEIGHT)
            table.setSelectionMode(QAbstractItemView.NoSelection)
            table.setStyleSheet('QTableWidget::item { padding-left: 10px }')
        
        self.counts = {
            'boundaries': 0,
            'contours'  : 0,
            'maps'      : 0,
            'places'    : 0
            }
        
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_boundaries_tab(), 'Boundaries (0)')
        self.tabs.addTab(self._create_contours_tab(), 'Contours (0)')
        self.tabs.addTab(self._create_maps_tab(), 'Maps (0)')
        self.tabs.addTab(self._create_places_tab(), 'Places (0)')
        layout.addWidget(self.tabs)
        layout.addWidget(self._create_buttons())
        self.setLayout(layout)
        
    def _browse(self, data_type: str, mode: QFileDialog.FileMode):
        '''
        Executes file dialog, then updates path field in current tab.
        
        Parameters:
            data_type (str) -- tab name
            mode (QFileDialog.FileMode) -- directory or file
        '''
        dlg = QFileDialog()
        if mode == QFileDialog.Directory:
            path = dlg.getExistingDirectory()
        elif mode == QFileDialog.ExistingFile:
            path = dlg.getOpenFileName(filter=self.filters[data_type])[0]
        if path == '':
            pass
        else:
            self.fields[f'{data_type}_path'].setText(path.replace('/', '\\'))
    
    def _create_boundaries_tab(self) -> QWidget:
        '''
        Creates boundary tab.
        
        Return type:
            QWidget
        '''
        layout = QVBoxLayout()
        
        # Options
        # -------
        sublayout = QGridLayout()
        
        # Row 0
        sublayout.addWidget(self.labels['boundaries_source'], 0, 1, 1, 1)
        subsublayout = QHBoxLayout()
        button = self.buttons['boundaries_folder']
        button.setChecked(True)
        button.toggled.connect(partial(self._toggle_source_type, 'boundaries'))
        subsublayout.addWidget(button)
        subsublayout.addWidget(self.buttons['boundaries_file'])
        subsublayout.addStretch()
        sublayout.addLayout(subsublayout, 0, 2, 1, -1)
        
        # Row 1
        sublayout.addWidget(self.labels['boundaries_path'], 1, 1, 1, 1)
        field = self.fields['boundaries_path']
        field.textChanged.connect(partial(self._load_items, 'boundaries'))
        sublayout.addWidget(field, 1, 2, 1, 1)
        button = self.buttons['browse_boundaries']
        button.setFixedWidth(self.BUTTON_WIDTH)
        button.clicked.connect(
            partial(self._browse, 'boundaries', QFileDialog.Directory))
        sublayout.addWidget(button, 1, 3, 1, 1)
        
        # Row 2
        sublayout.addWidget(self.labels['boundaries_enforce'], 2, 1, 1, 1)
        button = self.buttons['enforce_boundaries']
        sublayout.addWidget(button, 2, 2, 1, -1)
        
        for row in range(sublayout.rowCount()):
            sublayout.setRowMinimumHeight(row, self.ROW_HEIGHT)
        
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setLayout(sublayout)
        layout.addWidget(frame)
        
        # Items
        # -----
        layout.addWidget(self.tables['boundaries'])
        
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    def _create_contours_tab(self) -> QWidget:
        '''
        Creates contours tab.
        
        Return type:
            QWidget
        '''
        layout = QVBoxLayout()
        
        # Options
        # -------
        sublayout = QGridLayout()
        
        # Row 0
        sublayout.addWidget(self.labels['contours_source'], 0, 1, 1, 1)
        subsublayout = QHBoxLayout()
        button = self.buttons['contours_folder']
        button.setChecked(True)
        button.toggled.connect(partial(self._toggle_source_type, 'contours'))
        subsublayout.addWidget(button)
        subsublayout.addWidget(self.buttons['contours_file'])
        subsublayout.addStretch()
        sublayout.addLayout(subsublayout, 0, 2, 1, -1)
        
        # Row 1
        sublayout.addWidget(self.labels['contours_path'], 1, 1, 1, 1)
        field = self.fields['contours_path']
        field.textChanged.connect(partial(self._load_items, 'contours'))
        sublayout.addWidget(field, 1, 2, 1, 1)
        button = self.buttons['browse_contours']
        button.setFixedWidth(self.BUTTON_WIDTH)
        button.clicked.connect(
            partial(self._browse, 'contours', QFileDialog.Directory))
        sublayout.addWidget(button, 1, 3, 1, 1)
        
        # Row 2
        sublayout.addWidget(self.labels['contours_interval'], 2, 1, 1, 1)
        field = self.fields['contour_interval']
        field.setRange(1, 500)
        field.setValue(10)
        field.setSuffix(' m')
        sublayout.addWidget(field, 2, 2, 1, -1)
        
        for row in range(sublayout.rowCount()):
            sublayout.setRowMinimumHeight(row, self.ROW_HEIGHT)
        
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setLayout(sublayout)
        layout.addWidget(frame)
        
        # Items
        # -----
        layout.addWidget(self.tables['contours'])
        
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    def _create_maps_tab(self) -> QWidget:
        '''
        Creates maps tab.
        
        Return type:
            QWidget
        '''
        layout = QVBoxLayout()
        
        # Options
        # -------
        sublayout = QGridLayout()
        
        # Row 0
        sublayout.addWidget(self.labels['maps_source'], 0, 1, 1, 1)
        subsublayout = QHBoxLayout()
        button = self.buttons['maps_folder']
        button.setChecked(True)
        button.toggled.connect(partial(self._toggle_source_type, 'maps'))
        subsublayout.addWidget(button)
        subsublayout.addWidget(self.buttons['maps_file'])
        subsublayout.addStretch()
        sublayout.addLayout(subsublayout, 0, 2, 1, -1)
        
        # Row 1
        sublayout.addWidget(self.labels['maps_path'], 1, 1, 1, 1)
        field = self.fields['maps_path']
        field.textChanged.connect(partial(self._load_items, 'maps'))
        sublayout.addWidget(field, 1, 2, 1, 1)
        button = self.buttons['browse_maps']
        button.setFixedWidth(self.BUTTON_WIDTH)
        button.clicked.connect(
            partial(self._browse, 'maps', QFileDialog.Directory))
        sublayout.addWidget(button, 1, 3, 1, 1)
        
        for row in range(sublayout.rowCount()):
            sublayout.setRowMinimumHeight(row, self.ROW_HEIGHT)
        
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setLayout(sublayout)
        layout.addWidget(frame)
        
        # Items
        # -----
        layout.addWidget(self.tables['maps'])
        
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    def _create_places_tab(self) -> QWidget:
        '''
        Creates places tab.
        
        Return type:
            QWidget
        '''
        layout = QVBoxLayout()
        
        # Options
        # -------
        sublayout = QGridLayout()
        
        # Row 0
        sublayout.addWidget(self.labels['places_source'], 0, 1, 1, 1)
        subsublayout = QHBoxLayout()
        button = self.buttons['places_folder']
        button.setEnabled(False)
        button.toggled.connect(partial(self._toggle_source_type, 'places'))
        subsublayout.addWidget(button)
        button = self.buttons['places_file']
        button.setChecked(True)
        subsublayout.addWidget(button)
        subsublayout.addWidget(self.buttons['places_file'])
        subsublayout.addStretch()
        sublayout.addLayout(subsublayout, 0, 2, 1, -1)
        
        # Row 1
        sublayout.addWidget(self.labels['places_path'], 1, 1, 1, 1)
        field = self.fields['places_path']
        field.textChanged.connect(self._load_places)
        sublayout.addWidget(field, 1, 2, 1, 1)
        button = self.buttons['browse_places']
        button.setFixedWidth(self.BUTTON_WIDTH)
        button.clicked.connect(
            partial(self._browse, 'places', QFileDialog.ExistingFile))
        sublayout.addWidget(button, 1, 3, 1, 1)
        
        for row in range(sublayout.rowCount()):
            sublayout.setRowMinimumHeight(row, self.ROW_HEIGHT)
        
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setLayout(sublayout)
        layout.addWidget(frame)
        
        # Items
        # -----
        layout.addWidget(self.tables['places'])
        
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    def _create_buttons(self) -> QDialogButtonBox:
        '''
        Creates button box.

        Return type:
            QDialogButtonBox
        '''
        box = QDialogButtonBox()
        button = box.addButton(QDialogButtonBox.Reset)
        button.setText('Invert Selection')
        button.clicked.connect(self._invert)
        button = box.addButton(QDialogButtonBox.Ok)
        button.setText('Run')
        button.clicked.connect(self.accept)
        button = box.addButton(QDialogButtonBox.Cancel)
        button.clicked.connect(self.reject)
        return box
    
    def _current_tab_name(self) -> str:
        '''
        Returns current tab name.
        
        Return type:
            str
        '''
        return self.tabs.tabText(self.tabs.currentIndex()).split()[0].lower()
    
    def _get_checked_paths(self, tab_name: str) -> List[str]:
        '''
        Returns paths corresponding to checked items.
        
        Parameters:
            tab_name (str) -- name of tab
        
        Returns:
            List[str] -- list of paths corresponding to checked items
        '''
        source_path = self.fields[f'{tab_name}_path'].text()
        table = self.tables[tab_name]
        if table.rowCount() == 0:
            return []
        else:
            paths = []
            if os.path.isdir(source_path):
                for row in range(table.rowCount()):
                    box = table.cellWidget(row, 0)
                    if box.isEnabled() and box.isChecked():
                        paths.append(os.path.join(source_path, box.text()))
            else:
                box = table.cellWidget(0, 0)
                if box.isEnabled() and box.isChecked():
                    paths.append(source_path)
            return paths
    
    def _invert(self):
        '''
        Inverts selection in current tab. This function is called when the
        'Invert Selection' button is clicked.
        '''
        table = self.tables[self._current_tab_name()]
        for row in range(table.rowCount()):
            box = table.cellWidget(row, 0)
            if box.isEnabled():
                box.toggle()
    
    def _load_items(self, data_type: str, path: str):
        '''
        Loads file names from path into table view. This function is called 
        when the path field is a tab is altered.
        
        Parameters:
            data_type (str) -- tab name
            path (str) -- directory or file path
        '''
        if os.path.isdir(path):
            names = os.listdir(path)
            names = list(filter(
                lambda p: os.path.splitext(p)[1] == self.extensions[data_type],
                names
                ))
        else:
            if os.path.splitext(path)[1] == self.extensions[data_type]:
                names = [os.path.basename(path)]
            else:
                names = []
        
        COUNT = 0
        table = self.tables[data_type]
        table.setRowCount(len(names))
        for row, name in enumerate(names):
            box = QCheckBox(name)
            box.setChecked(True)
            if name in self.existing[data_type]:
                box.setEnabled(False)
            else:
                COUNT += 1
            box.toggled.connect(partial(self._update_count, data_type))
            table.setCellWidget(row, 0, box)
        
        self.counts[data_type] = COUNT
        self.tabs.setTabText(
            self.tabs.currentIndex(), f'{data_type.capitalize()} ({COUNT})')
    
    def _load_places(self, path: str):
        '''
        Loads place attributes from source file into table view.
        
        Parameters:
            data_type (str) -- tab name
            path (str) -- directory or file path
        '''
        try:
            places = list(pd.read_csv(path, index_col=0).to_records())
        except:
            places = []
        
        COUNT = 0
        table = self.tables['places']
        table.setRowCount(len(places))
        for row, (ID, name, *_) in enumerate(places):
            box = QCheckBox(f'{ID} - {name}')
            box.setChecked(True)
            if ID in self.existing['places']:
                box.setEnabled(False)
            else:
                COUNT += 1
            box.toggled.connect(partial(self._update_count, 'places'))
            table.setCellWidget(row, 0, box)
        
        self.counts['places'] = COUNT
        tabs = self.tabs
        tabs.setTabText(
            tabs.currentIndex(), f'Places ({COUNT})')
    
    def _toggle_source_type(self, data_type: str, checked: bool):
        '''
        Reconnects browse button when source type is changed.
        
        Parameters:
            data_type (str) -- tab name
            checked (bool) -- whether 'Directory' is selected
        '''
        self.fields[f'{data_type}_path'].clear()
        button = self.buttons[f'browse_{data_type}']
        button.clicked.disconnect()
        if checked:
            button.clicked.connect(
                partial(self._browse, data_type, QFileDialog.Directory))
        else:
            button.clicked.connect(
                partial(self._browse, data_type, QFileDialog.ExistingFile))
    
    def _update_count(self, data_type: str, checked: bool):
        '''
        Updates item count and tab text when an item in a table is toggled.
        This function is called when the 'togged' signal is emitted from a
        check box.
        
        Parameters:
            data_type (str) -- tab name
            checked (bool) -- whether item was checked or unchecked
        '''
        if checked:
            self.counts[data_type] += 1
        else:
            self.counts[data_type] -= 1
        self.tabs.setTabText(
            self.tabs.currentIndex(),
            f'{data_type.capitalize()} ({self.counts[data_type]})')
    
    def accept(self):
        self.queues = {'boundaries': self._get_checked_paths('boundaries'),
                       'contours'  : self._get_checked_paths('contours'),
                       'maps'      : self._get_checked_paths('maps'),
                       'places'    : self._get_checked_paths('places')}
        super().accept()


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = GrapherDialog()
    dlg.show()
    sys.exit(app.exec_())


if __name__ == '__console__':
    dlg = GrapherDialog()
    dlg.show()
