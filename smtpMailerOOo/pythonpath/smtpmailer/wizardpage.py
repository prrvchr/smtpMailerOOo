#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.ui.dialogs import XWizardPage
from com.sun.star.util import XRefreshListener
from com.sun.star.container import XContainerListener
from com.sun.star.awt.grid import XGridSelectionListener
from com.sun.star.view.SelectionType import MULTI
from com.sun.star.awt.PosSize import POSSIZE
from com.sun.star.util.MeasureUnit import APPFONT
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from unolib import PropertySet
from unolib import createService
from unolib import getProperty
from unolib import getStringResource
from unolib import getDialogUrl

from .griddatamodel import GridDataModel
from .dbtools import getRowResult
from .logger import logMessage

from .configuration import g_identifier
from .configuration import g_extension
from .configuration import g_column_index

import traceback


class WizardPage(unohelper.Base,
                 PropertySet,
                 XWizardPage,
                 XRefreshListener,
                 XGridSelectionListener):
    def __init__(self, ctx, parent, id, handler):
        msg = "PageId: %s ..." % id
        print("wizardpage.__init__() 1")
        self.ctx = ctx
        self.PageId = id
        provider = createService(ctx, 'com.sun.star.awt.ContainerWindowProvider')
        url = getDialogUrl(g_extension, 'PageWizard%s' % id)
        print("wizardpage.__init__() 2")
        self.Window = provider.createContainerWindow(url, '', parent, handler)
        self._handler = handler
        self._initPage()
        print("wizardpage.__init__() 3")
        msg += " Done"
        logMessage(self.ctx, INFO, msg, 'WizardPage', '__init__()')

    def _initPage(self):
        try:
            if self.PageId == 1:
                print("wizardpage.initPage() 1 1")
                control = self.Window.getControl('ListBox1')
                datasources = self._handler.DataSources
                control.Model.StringItemList = datasources
                datasource = self._handler.getDocumentDataSource()
                print("wizardpage.initPage() 1 2 %s-%s" % (datasources, datasource))
                if datasource in datasources:
                    print("wizardpage.initPage() 1 3")
                    self._handler._changeDataSource(self.Window, datasource)
                    print("wizardpage.initPage() 1 4")
                    #self._handler._initColumnsSetting(self.Window)
                    print("wizardpage.initPage() 1 5")
                    self._handler._disabled = True
                    print("wizardpage.initPage() 1 6")
                    control.selectItem(datasource, True)
                    print("wizardpage.initPage() 1 7")
                    self._handler._disabled = False
                print("wizardpage.initPage() 1 8")
            elif self.PageId == 2:
                print("wizardpage.initPage() 2 1")
                point = uno.createUnoStruct('com.sun.star.awt.Point', 10, 60)
                size = uno.createUnoStruct('com.sun.star.awt.Size', 115, 115)
                grid1 = self._getGridControl(self._handler._address, 'Addresses', point, size)
                self.Window.addControl('GridControl1', grid1)
                grid1.addSelectionListener(self)
                point.X = 160
                grid2 = self._getGridControl(self._handler._recipient, 'Recipients', point, size)
                self.Window.addControl('GridControl2', grid2)
                grid2.addSelectionListener(self)
                self._handler.addRefreshListener(self)
                self._handler._recipient.execute()
                self._refreshPage2()
                #mri = createService(self.ctx, 'mytools.Mri')
                #mri.inspect(grid1)
                print("wizardpage.initPage() 2 2")
            elif self.PageId == 3:
                pass
        except Exception as e:
            msg = u"Error: %s" % traceback.print_exc()
            logMessage(self.ctx, SEVERE, msg, 'WizardPage', 'initPage()')

    # XRefreshListener
    def refreshed(self, event):
        tag = event.Source.Model.Tag
        if self.PageId == 1:
            pass
        elif self.PageId == 2 and tag == 'DataSource':
            self._refreshPage2()
        elif self.PageId == 3:
            pass

    # XGridSelectionListener
    def selectionChanged(self, event):
        tag = event.Source.Model.Tag
        enabled = event.Source.hasSelectedRows()
        if tag == 'Addresses':
            self.Window.getControl("CommandButton2").Model.Enabled = enabled
        elif tag == 'Recipients':
            self.Window.getControl("CommandButton3").Model.Enabled = enabled
            if enabled:
                index = event.Source.getSelectedRows()[0]
                if index != self._handler.index:
                    self._handler.setDocumentRecord(index)

    # XContainerListener
    def elementInserted(self, event):
        print("WizardPage.elementInserted()")
        mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
        mri.inspect(event)
    def elementRemoved(self, event):
        print("WizardPage.elementRemoved()")
        mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
        mri.inspect(event)
    def elementReplaced(self, event):
        print("WizardPage.elementReplaced()")
        mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
        mri.inspect(event)

    # XRefreshListener, XGridSelectionListener, XContainerListener
    def disposing(self, event):
        pass

    # XWizardPage
    def activatePage(self):
        # TODO: LibreOffice displays only the first page of the path if you do not manually manage
        # TODO: the visibility of pages on XWizardPage.activatePage() and XWizardPage.commitPage()
        # TODO: reported: Bug 132661 https://bugs.documentfoundation.org/show_bug.cgi?id=132661
        self.Window.setVisible(True)
        msg = "PageId: %s ..." % self.PageId
        if self.PageId == 1:
            pass
        elif self.PageId == 2:
            pass
        elif self.PageId == 3:
            pass
        msg += " Done"
        logMessage(self.ctx, INFO, msg, 'WizardPage', 'activatePage()')

    def commitPage(self, reason):
        try:
            msg = "PageId: %s ..." % self.PageId
            forward = uno.getConstantByName('com.sun.star.ui.dialogs.WizardTravelType.FORWARD')
            backward = uno.getConstantByName('com.sun.star.ui.dialogs.WizardTravelType.BACKWARD')
            finish = uno.getConstantByName('com.sun.star.ui.dialogs.WizardTravelType.FINISH')
            # TODO: LibreOffice displays only the first page of the path if you do not manually manage
            # TODO: the visibility of pages on XWizardPage.activatePage() and XWizardPage.commitPage()
            # TODO: reported: Bug 132661 https://bugs.documentfoundation.org/show_bug.cgi?id=132661
            self.Window.setVisible(False)
            if self.PageId == 1:
                if self._handler._modified:
                    self._handler.saveSetting(self.Window)
                    self._handler._database.DatabaseDocument.store()
            elif self.PageId == 2:
                print("wizardpage.commitPage() 1")
                #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
                #mri.inspect(self._handler._database)
                if self._handler._modified:
                    self._handler.saveSelection()
                    self._handler._database.DatabaseDocument.store()
                print("wizardpage.commitPage() 2")
            elif self.PageId == 3:
                pass
            msg += " Done"
            logMessage(self.ctx, INFO, msg, 'WizardPage', 'commitPage()')
            return True
        except Exception as e:
            print("WizardPage.commitPage() ERROR: %s - %s" % (e, traceback.print_exc()))

    def canAdvance(self):
        advance = False
        #print("wizardpage.canAdvance() 1 %s" % advance)
        if self.PageId == 1:
            advance = self._handler.Connection is not None
            advance &= self.Window.getControl("ListBox5").ItemCount != 0
        elif self.PageId == 2:
            advance = self._handler._recipient.RowCount != 0
        elif self.PageId == 3:
            pass
        #print("wizardpage.canAdvance() 2 %s" % advance)
        return advance

    def _getGridControl(self, rowset, tag, point, size, flags=POSSIZE):
        # TODO: Because we need a GridDataListener who listen change on the GridDataModel
        # TODO: We need to re assign the Model, and not only just set the GridDataModel
        model = self._getGridModel(tag)
        control = createService(self.ctx, model.DefaultControl)
        control.setModel(self._getGridDataModel(model, rowset))
        s = self.Window.convertSizeToPixel(size, APPFONT)
        p = self.Window.convertPointToPixel(point, APPFONT)
        control.setPosSize(p.X, p.Y, s.Width, s.Height, flags)
        return control

    def _getGridModel(self, tag):
        model = self.Window.Model.createInstance('com.sun.star.awt.grid.UnoControlGridModel')
        model.SelectionModel = MULTI
        #model.ShowRowHeader = True
        model.BackgroundColor = 16777215
        model.Tag = tag
        return model

    def _getGridDataModel(self, model, rowset):
        data = GridDataModel(self.ctx, rowset)
        model.GridDataModel = data
        model.ColumnModel = data.ColumnModel
        return model

    def _refreshPage2(self):
        self._handler.refreshTables(self.Window.getControl('ListBox1'))

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['PageId'] = getProperty('PageId', 'short', readonly)
        properties['Window'] = getProperty('Window', 'com.sun.star.awt.XWindow', readonly)
        return properties
