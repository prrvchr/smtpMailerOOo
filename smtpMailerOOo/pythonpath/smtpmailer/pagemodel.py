#!
# -*- coding: utf_8 -*-

"""
╔════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                    ║
║   Copyright (c) 2020 https://prrvchr.github.io                                     ║
║                                                                                    ║
║   Permission is hereby granted, free of charge, to any person obtaining            ║
║   a copy of this software and associated documentation files (the "Software"),     ║
║   to deal in the Software without restriction, including without limitation        ║
║   the rights to use, copy, modify, merge, publish, distribute, sublicense,         ║
║   and/or sell copies of the Software, and to permit persons to whom the Software   ║
║   is furnished to do so, subject to the following conditions:                      ║
║                                                                                    ║
║   The above copyright notice and this permission notice shall be included in       ║
║   all copies or substantial portions of the Software.                              ║
║                                                                                    ║
║   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,                  ║
║   EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES                  ║
║   OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.        ║
║   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY             ║
║   CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,             ║
║   TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE       ║
║   OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                    ║
║                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════╝
"""

import uno
import unohelper

from com.sun.star.sdb.CommandType import TABLE

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from unolib import KeyMap
from unolib import createService
from unolib import getConfiguration
from unolib import getStringResource
from unolib import getPropertyValueSet

from .wizardtools import getRowSetOrders

from .configuration import g_identifier
from .configuration import g_extension
from .configuration import g_fetchsize

from .logger import logMessage
from .logger import getMessage

import traceback


class PageModel(unohelper.Base):
    def __init__(self, ctx, email=None):
        self.ctx = ctx
        self._listeners = []
        self._disabled = False
        self._modified = False
        self._address = self._getRowSet()
        self._recipient = self._getRowSet()
        self._statement = None
        self._table = None
        self._database = None
        self._quey = None
        self._emailcolumns = self._indexcolumns = ()
        self.index = -1
        self._stringResource = getStringResource(self.ctx, g_identifier, g_extension)
        self._configuration = getConfiguration(self.ctx, g_identifier, True)

    @property
    def DataSources(self):
        dbcontext = createService(self.ctx, 'com.sun.star.sdb.DatabaseContext')
        return dbcontext.getElementNames()
    @property
    def Connection(self):
        if self._statement is not None:
            return self._statement.getConnection()
        return None
    @property
    def TableNames(self):
        if self.Connection is not None:
            return self.Connection.getTables().getElementNames()
        return ()
    @property
    def ColumnNames(self):
        if self._table is not None:
            return self._table.getColumns().getElementNames()
        return ()

    # XRefreshable
    def refresh(self):
        pass
    def addRefreshListener(self, listener):
        if listener not in self._listeners:
            self._listeners.append(listener)
    def removeRefreshListener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)
    def refreshControl(self, control):
        event = uno.createUnoStruct('com.sun.star.lang.EventObject', control)
        for listener in self._listeners:
            listener.refreshed(event)

    def resolveString(self, resource):
        return self._stringResource.resolveString(resource)

    def setDataSource(self, view, datasource):
        initialized = False
        print("PageModel.setDataSource() 1")
        database = self._getDatabase(datasource)
        if database is not None:
            if database.IsPasswordRequired:
                handler = createService(self.ctx, 'com.sun.star.task.InteractionHandler')
                connection = database.getConnectionWithCompletion(handler)
            else:
                connection = database.getConnection('', '')
            self._database = database
            self._statement = connection.createStatement()
            document, form = self._getForm(False)
            self._table = self.getDefaultTable(document, 'PrimaryTable')
            view.setTables(self.TableNames, self._table.Name)
            column = self.getDefaultColumn(self._table)
            view.setColumns(self.ColumnNames, column)
            emails = self.getEmailColumn(document, 'EmailColumns')
            view.setEmailAddress(emails)
            keys = self.getIndexColumns(document, 'IndexColumns')
            view.setPrimaryKey(keys)
            if form is not None:
                form.close()
            view.updateControlByTag('Columns')
            view.updateControlByTag('EmailAddress')
            view.updateControlByTag('PrimaryKey')
            #self.refreshControl(self._getDataSource())
            self._query = self._getQueryComposer()
            self._setRowSet(datasource)
            print("PageModel.setDataSource() 2")
            initialized = True
        else:
            self._table = None
            self._database = None
            self._statement = None
        print("PageModel.setDataSource() 3")
        return initialized

    def setAddressBook(self, view, table):
        print("PageModel.setAddressBook() 1")
        old = self._tables.getColumns().getElementNames()
        self._table = self.Connection.getTables().getByName(table)
        #self._address.UpdateTableName = table
        self._address.Command = table
        self._address.Filter = self._getFilter(True)
        self._address.ApplyFilter = True
        self._address.execute()
        print("PageModel.setAddressBook() 2")
        new = self._table.getColumns().getElementNames()
        return old != new

    def getEmailColumn(self, document, property):
        items = self._getDocumentList(document, property)
        self._emailcolumns = items
        return items

    def getIndexColumns(self, document, property):
        items = self._getDocumentList(document, property)
        self._indexcolumns = items
        return items

    def getDefaultTable(self, document, property):
        default = self.Connection.getTables().getByIndex(0)
        name = self._getDocumentValue(document, property, default.Name)
        if self.Connection.getTables().hasByName(name):
            default = self.Connection.getTables().getByName(name)
        return default

    def getDefaultColumn(self, table):
        return table.getColumns().getByIndex(0).Name

    def initColumns(self, view, name=None):
        if name is None:
            table = self.Connection.getTables().getByIndex(0)
        else:
            table = self.Connection.getTables().getByName(name)
        self._recipient.Command = table.Name
        columns = table.getColumns().getElementNames()
        view.setColumns(columns, self.getDefaultColumn(table))

    def getDocumentDataSource(self):
        datasource = ''
        setting = 'com.sun.star.document.Settings'
        document = createService(self.ctx, 'com.sun.star.frame.Desktop').CurrentComponent
        if document.supportsService('com.sun.star.text.TextDocument'):
            datasource = document.createInstance(setting).CurrentDatabaseDataSource
        return datasource

    def _getDatabase(self, datasource):
        database = None
        dbcontext = createService(self.ctx, 'com.sun.star.sdb.DatabaseContext')
        if dbcontext.hasByName(datasource):
            database = dbcontext.getByName(datasource)
        return database

    def _getQueryComposer(self):
        composer = self.Connection.createInstance('com.sun.star.sdb.SingleSelectQueryComposer')
        query = self._getQuery(False)
        composer.setQuery(query.Command)
        self._address.Command = query.UpdateTableName
        print("PageModel._getQueryComposer() %s - %s" % (query.UpdateTableName, query.Command))
        return composer

    def _getQuery(self, create, name='smtpMailerOOo'):
        queries = self._database.getQueryDefinitions()
        if queries.hasByName(name):
            query = queries.getByName(name)
        elif create:
            query = createService(self.ctx, 'com.sun.star.sdb.QueryDefinition')
            queries.insertByName(name, query)
        else:
            query = createService(self.ctx, 'com.sun.star.sdb.QueryDefinition')
            table = self.Connection.getTables().getByIndex(0)
            column = table.getColumns().getByIndex(0)
            query.Command = 'SELECT * FROM "%s" WHERE 0=1 ORDER BY "%s"' % (table.Name, column.Name)
            query.UpdateTableName = table.Name
        return query

    def _getForm(self, create, name='smtpMailerOOo'):
        doc, form = None, None
        forms = self._database.DatabaseDocument.getFormDocuments()
        if forms.hasByName(name):
            form = forms.getByName(name)
        elif create:
            form = self._createForm(forms, name)
        if form is not None:
            args = getPropertyValueSet({'ActiveConnection': self.Connection,
                                        'OpenMode': 'openDesign',
                                        'Hidden': True})
            doc = forms.loadComponentFromURL(name, '', 0, args)
        return doc, form

    def _getDocumentValue(self, document, property, default=None):
        value = default
        print("PageModel._getDocumentValue() %s" % (property, ))
        if document is not None:
            properties = document.DocumentProperties.UserDefinedProperties
            if properties.PropertySetInfo.hasPropertyByName(property):
                print("PageModel._getDocumentValue() getProperty")
                value = properties.getPropertyValue(property)
            elif default is not None:
                self._setDocumentValue(document, property, default)
        return value

    def _getDocumentList(self, document, property):
        items = ()
        value = self._getDocumentValue(document, property)
        if value is not None:
            items = tuple(value.split(','))
        return items

    def _setDocumentValue(self, document, property, value):
        print("PageModel._setDocumentValue() %s - %s" % (property, value))
        properties = document.DocumentProperties.UserDefinedProperties
        if properties.PropertySetInfo.hasPropertyByName(property):
            print("PageModel._setDocumentValue() setProperty")
            properties.setPropertyValue(property, value)
        else:
            print("PageModel._setDocumentValue() addProperty")
            properties.addProperty(property,
            uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID') +
            uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND') +
            uno.getConstantByName('com.sun.star.beans.PropertyAttribute.REMOVABLE') +
            uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEDEFAULT'),
            value)

    def _createForm(self, forms, name):
        service = 'com.sun.star.sdb.DocumentDefinition'
        args = getPropertyValueSet({'Name': name, 'ActiveConnection': self.Connection})
        form = forms.createInstanceWithArguments(service, args)
        forms.insertByName(name, form)
        form = forms.getByName(name)
        return form

    def _setRowSet(self, datasource):
        self._address.DataSourceName = self._recipient.DataSourceName = datasource
        self._address.Order = self._recipient.Order = self._query.getOrder()
        self._recipient.Command = self._query.getTables().getByIndex(0).Name
        self._recipient.Filter = self._query.getFilter()
        print("PageModel._setRowSet() %s - %s" % (self._query.ElementaryQuery, self._query.getFilter()))
        self._recipient.ApplyFilter = True
        self._recipient.execute()

    def _getFilter(self, any=False):
        filters = []
        for column in self._emailcolumns:
            if column in self.ColumnNames:
                filters.append('"%s" IS NOT NULL' % column)
        filter = self._addFilter(filters, any)
        print("PageModel._getFilter() %s" % filter)
        return filter

    def _addFilter(self, filters, any=False):
        separator = ' OR ' if any else ' AND '
        filter = separator.join(filters)
        if len(filters) > 1:
            filter = '(%s)' % filter
        return filter

    def getOrderIndex(self):
        index = []
        orders = getRowSetOrders(self._recipient)
        columns = self.ColumnNames
        for order in orders:
            if order in columns:
                index.append(columns.index(order))
        return tuple(index)

    # TODO: XRowset.Order should be treated as a stack where:
    # TODO: adding is done at the end and removing will keep order.
    def setOrderColumn(self, view, columns):
        print("PageModel.setOrderColumn() 1")
        self._modified = True
        orders = getRowSetOrders(self._recipient)
        print("PageModel.setOrderColumn() 2: %s - %s" % (orders, columns))
        for order in reversed(orders):
            if order not in columns:
                orders.remove(order)
        for column in columns:
            if column not in orders:
                orders.append(column)
        order = '"%s"' % '", "'.join(orders) if len(orders) else ''
        print("PageModel.setOrderColumn() 3: %s" % order)
        self._query.setOrder(order)
        self._setRowSetOrder()
        view.refreshGridButton()
        print("PageModel.setOrderColumn() 4")

    def _getRowSet(self):
        rowset = createService(self.ctx, 'com.sun.star.sdb.RowSet')
        rowset.CommandType = TABLE
        print("PageModel._getRowSet() %s" % rowset.FetchSize)
        #rowset.FetchSize = g_fetchsize
        return rowset

    def _setRowSetOrder(self):
        print("PageModel._setRowSetOrder() 1")
        self._recipient.Order = self._address.Order = self._query.getOrder()
        print("PageModel._setRowSetOrder() 2")
        self._address.execute()
        print("PageModel._setRowSetOrder() 3")
        self._recipient.execute()
        print("PageModel._setRowSetOrder() 4")
