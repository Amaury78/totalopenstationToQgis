# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TotalopenstationDialog
                                 A QGIS plugin
 Total Open Station (TOPS for friends) is a free software program for downloading and processing data from total station devices.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-09-01
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Enzo Cocca adArte srl; Stefano Costa
        email                : enzo.ccc@gmail.com
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

import os
import time, sys
from time import sleep
import threading
import subprocess
import platform
import csv
import tempfile
from qgis.PyQt import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtCore import  *
from qgis.PyQt.QtWidgets import QVBoxLayout, QApplication, QDialog, QMessageBox, QFileDialog,QLineEdit,QWidget,QCheckBox,QProgressBar
from qgis.PyQt.QtSql import *
from qgis.PyQt.uic import loadUiType
from qgis.PyQt import  QtWidgets 
from qgis.core import  *
from qgis.gui import  *
from qgis.utils import iface
from numpy import interp
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'totalstation_dialog_base.ui'))


class Progress:
    def __init__(self, value, end, title='Downloading',buffer=20):
        self.title = title
        #when calling in a for loop it doesn't include the last number
        self.end = end -1
        self.buffer = buffer
        self.value = value
        self.progress()

    def progress(self):
        maped = int(interp(self.value, [0, self.end], [0, self.buffer]))
        print(f'{self.title}: [{"#"*maped}{"-"*(self.buffer - maped)}]{self.value}/{self.end} {((self.value/self.end)*100):.2f}%', end='\r')


class progressThread(QThread):

    progress_update = QtCore.pyqtSignal(int) # or pyqtSignal(int)

    def __init__(self):
        QThread.__init__(self)

    def __del__(self):
        self.wait()


    def run(self):
        # your logic here
        while 1:      
            maxVal = 1 # NOTE THIS CHANGED to 1 since updateProgressBar was updating the value by 1 every time
            self.progress_update.emit(maxVal) # self.emit(SIGNAL('PROGRESS'), maxVal)
            # Tell the thread to sleep for 1 second and let other things run
            time.sleep(1)



class TotalopenstationDialog(QtWidgets.QDialog, FORM_CLASS):
    
    
    def __init__(self, parent=None):
        """Constructor."""
        super(TotalopenstationDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.progress_thread = progressThread()
        #self.progress_thread.start()
        self.progress_thread.progress_update.connect(self.updateProgressBar)
        self.model = QtGui.QStandardItemModel(self)
        self.tableView.setModel(self.model)
        self.toolButton_input.clicked.connect(self.setPathinput)
        self.toolButton_output.clicked.connect(self.setPathoutput)
        self.toolButton_save_raw.clicked.connect(self.setPathsaveraw)
        self.mDockWidget.setHidden(True)
        self.comboBox_model.currentIndexChanged.connect(self.tt)
        self.lineEdit_save_raw.textChanged.connect(self.connect)
        self.pushButton_connect.setEnabled(False)
        
    def connect(self):
        
        
        if str(self.lineEdit_save_raw.text()):
            
            self.pushButton_connect.setEnabled(True)
        
        else:
            self.pushButton_connect.setEnabled(False)
    
    def updateProgressBar(self, maxVal):
        self.progressBar.setValue(self.progressBar.value() + maxVal)
    
        if maxVal == 0:
            self.progressBar.setValue(100)
    
    def tt(self):    
        if self.comboBox_model.currentIndex()!=6:
            
            self.mDockWidget.setHidden(True)
        else:
            
            self.mDockWidget.show()
        #self.format_()
    
    # def format_(self):
        # if self.comboBox_format.currentIndex()==0:
            # return 'tsj'
    
        # if self.comboBox_format.currentText()==1:
            # return 'gsi'
    
        # if self.comboBox_format.currentText()==4:
            # return 'v200'
        
        # if self.comboBox_format.currentText()==5:
            # return 'sdr'
    
        # if self.comboBox_format.currentText()==6:
            # return 'are'
    
        # if self.comboBox_format.currentText()==7 :
            # return '*'
    
        # if self.comboBox_format.currentText()==9 :
            # return 'rw5'
    def setPathinput(self):
        s = QgsSettings()
        input_ = QFileDialog.getOpenFileName(
            self,
            "Set file name",
            '',
            "(*.*)"
        )[0]
        #filename=dbpath.split("/")[-1]
        if input_:

            self.lineEdit_input.setText(input_)
            s.setValue('',input_)
            # r=open(self.lineEdit_input.text(),'r')
            # lines = r.read().split(',')
            # self.textEdit.setText(str(lines))
    
    
    
    def setPathoutput(self):
        s = QgsSettings()
        output_ = QFileDialog.getSaveFileName(
            self,
            "Set file name",
            '',
            "(*.{})".format(self.comboBox_format2.currentText())
        )[0]
        #filename=dbpath.split("/")[-1]
        if output_:

            self.lineEdit_output.setText(output_)
            s.setValue('',output_)
            
    def setPathsaveraw(self):
        s = QgsSettings()
        output_ = QFileDialog.getSaveFileName(
            self,
            "Set file name",
            '',
            "(*.tops)"
        )[0]
        #filename=dbpath.split("/")[-1]
        if output_:

            self.lineEdit_save_raw.setText(output_)
            s.setValue('',output_)
    
    def loadCsv(self, fileName):
        self.tableView.clearSpans()
        with open(fileName, "r") as fileInput:
            for row in csv.reader(fileInput):    
                items = [
                    QtGui.QStandardItem(field)
                    for field in row
                ]
                self.model.appendRow(items)
    
    def delete(self):
        if self.tableView.selectionModel().hasSelection():
            indexes =[QPersistentModelIndex(index) for index in self.tableView.selectionModel().selectedRows()]
            for index in indexes:
                #print('Deleting row %d...' % index.row())
                self.model.removeRow(index.row())
    

    
    def on_pushButton_export_pressed(self):
        
        self.delete()
        if platform.system() == "Windows":
            b=QgsApplication.qgisSettingsDirPath().replace("/","\\")
                
                
            cmd = os.path.join(os.sep, b, 'python', 'plugins', 'totalopenstationToQgis', 'scripts', 'totalopenstation-cli-parser.py')
            cmd2= ' -i '+str(self.lineEdit_input.text())+' '+'-o '+str(self.lineEdit_output.text())+' '+'-f'+' '+self.comboBox_format.currentText()+' '+'-t'+' '+self.comboBox_format2.currentText()+' '+'--overwrite'
            try:#os.system("start cmd /k" + ' python ' +cmd+' '+cmd2)
                p=subprocess.check_call(['python',cmd, '-i',str(self.lineEdit_input.text()),'-o',str(self.lineEdit_output.text()),'-f',self.comboBox_format.currentText(),'-t',self.comboBox_format2.currentText(),'--overwrite'], shell=True)
                
                self.updateProgressBar(p)
            except Exception as e:
                
                self.textEdit.append('Connection falied!')   
                
            else:
                self.textEdit.append('Connection OK.................!\n\n\n')
                self.textEdit.append('Start dowload data.................!\n\n\n')
                # sleep(1)
                # self.textEdit.repaint()
                for x in range(21):  #set to 21 to include until 20
                    self.textEdit.append(str(Progress(x, 21)))
                
                self.textEdit.append('Dowload finished.................!\n\n\n')
                self.textEdit.append('Result:\n')
            #Load the layer if the format is geojson or dxf or csv           
            if self.comboBox_format2.currentIndex()== 0:
                
                layer = QgsVectorLayer(str(self.lineEdit_output.text()), 'totalopenstation', 'ogr')
                
                layer.isValid() 

                QgsProject.instance().addMapLayer(layer)

                QMessageBox.warning(self, 'Total Open Station luncher',
                                          'data loaded into panel Layer', QMessageBox.Ok)
            
                self.progressBar.reset()
                temp=tempfile.mkstemp(suffix = '.csv')
                QgsVectorFileWriter.writeAsVectorFormat(layer, 'test.csv', "utf-8", driverName = "CSV")
                
                self.loadCsv('test.csv')
            elif self.comboBox_format2.currentIndex()== 1:
                
                layer = QgsVectorLayer(str(self.lineEdit_output.text()), 'totalopenstation', 'ogr')
                
                layer.isValid() 

                
                QgsProject.instance().addMapLayer(layer)

                QMessageBox.warning(self, 'Total Open Station luncher',
                                          'data loaded into panel Layer', QMessageBox.Ok)
                self.progressBar.reset()                          
                temp=tempfile.mkstemp(suffix = '.csv')
                QgsVectorFileWriter.writeAsVectorFormat(layer, 'test.csv', "utf-8", driverName = "CSV")
                self.loadCsv('test.csv')                     
            
            elif self.comboBox_format2.currentIndex()== 2:
                uri = "file:///"+str(self.lineEdit_output.text())+"?type=csv&xField=x&yField=y&spatialIndex=no&subsetIndex=no&watchFile=no"
                layer = QgsVectorLayer(uri, 'totalopenstation', "delimitedtext")
                
                layer.isValid() 

                
                QgsProject.instance().addMapLayer(layer)

                QMessageBox.warning(self, 'Total Open Station luncher',
                                          'data loaded into panel Layer', QMessageBox.Ok)
            

                self.loadCsv(str(self.lineEdit_output.text()))
                
                

                self.progressBar.reset()
            else:
                self.progressBar.reset()
                pass
        else:
            b=QgsApplication.qgisSettingsDirPath()
            cmd = os.path.join(os.sep, b, 'python', 'plugins', 'totalopenstationToQgis', 'scripts', 'totalopenstation-cli-parser.py')
            cmd2= ' -i '+str(self.lineEdit_input.text())+' '+'-o '+str(self.lineEdit_output.text())+' '+'-f'+' '+self.comboBox_format.currentText()+' '+'-t'+' '+self.comboBox_format2.currentText()+' '+'--overwrite'
            #os.system("start cmd /k" + ' python ' +cmd+' '+cmd2)
            subprocess.check_call(['python',cmd, '-i',str(self.lineEdit_input.text()),'-o',str(self.lineEdit_output.text()),'-f',self.comboBox_format.currentText(),'-t',self.comboBox_format2.currentText(),'--overwrite'], shell=True)
            
            #Load the layer if the format is geojson or dxf or csv           
            if self.comboBox_format2.currentIndex()== 0:
                
                layer = QgsVectorLayer(str(self.lineEdit_output.text()), 'totalopenstation', 'ogr')
                
                layer.isValid() 

                QgsProject.instance().addMapLayer(layer)

                QMessageBox.warning(self, 'Total Open Station luncher',
                                          'data loaded into panel Layer', QMessageBox.Ok)
            
            
                r=open(str(self.lineEdit_output.text()),'r')
                lines = r.read().split(',')
                self.textEdit.setText(str(lines))
            elif self.comboBox_format2.currentIndex()== 1:
                
                layer = QgsVectorLayer(str(self.lineEdit_output.text()), 'totalopenstation', 'ogr')
                
                layer.isValid() 

                
                QgsProject.instance().addMapLayer(layer)

                QMessageBox.warning(self, 'Total Open Station luncher',
                                          'data loaded into panel Layer', QMessageBox.Ok)
                                          
                r=open(str(self.lineEdit_output.text()),'r')
                lines = r.read().split(',')
                self.textEdit.setText(str(lines))                          
            
            elif self.comboBox_format2.currentIndex()== 2:
                uri = "file:///"+str(self.lineEdit_output.text())+"?type=csv&xField=x&yField=y&spatialIndex=no&subsetIndex=no&watchFile=no"
                layer = QgsVectorLayer(uri, 'totalopenstation', "delimitedtext")
                
                layer.isValid() 

                
                QgsProject.instance().addMapLayer(layer)

                QMessageBox.warning(self, 'Total Open Station luncher',
                                          'data loaded into panel Layer', QMessageBox.Ok)
            

                self.loadCsv(str(self.lineEdit_output.text()))
                
                

            
            else:
                pass
    
    
       
    def on_pushButton_connect_pressed(self):
        self.textEdit.clear()
            
        if platform.system() == "Windows":
            b=QgsApplication.qgisSettingsDirPath().replace("/","\\")
            cmd = os.path.join(os.sep, b , 'python', 'plugins', 'totalopenstationToQgis', 'scripts', 'totalopenstation-cli-connector.py')
            # cmd2=' -m'+'  '+self.comboBox_model.currentText()+'  '+'-p'+'  '+self.comboBox_port.currentText()+'  '+'-o'+'  '+str(self.lineEdit_save_raw.text())
            # os.system("start cmd /k" + ' python ' +cmd+' '+cmd2)
            #c=''
            try:
                c=subprocess.check_call(['python', cmd,'-m',self.comboBox_model.currentText(),'-p',self.comboBox_port.currentText(),'-o',str(self.lineEdit_save_raw.text())], shell=True)
                
                self.updateProgressBar(c)
                layer = QgsVectorLayer(str(self.lineEdit_save_raw.text()), 'totalopenstation', 'ogr')
                    
                layer.isValid() 

                
                QgsProject.instance().addMapLayer(layer)

                QMessageBox.warning(self, 'Total Open Station luncher',
                                          'data loaded into panel Layer', QMessageBox.Ok)
            
                self.progressBar.reset()
                
                
            except Exception as e:
                if self.comboBox_port.currentText()=='':
                    self.textEdit.append('Insert port please!')
                
                self.textEdit.append('Connection falied!')   
                
            else:
                self.textEdit.append('Connection OK.................!\n\n\n')
                self.textEdit.append('Start dowload data.................!\n\n\n')
                for x in range(21):  #set to 21 to include until 20
                    self.textEdit.append(Progress(x, 21))
                
                self.textEdit.append('Dowload finished.................!\n\n\n')
                self.textEdit.append('Result:\n')
                r=open(str(self.lineEdit_save_raw.text()),'r')
                lines = r.read().split(',')
                self.textEdit.append(str(lines))
            
        else:
            b=QgsApplication.qgisSettingsDirPath()
            cmd = os.path.join(os.sep, b , 'python', 'plugins', 'totalopenstationToQgis', 'scripts', 'totalopenstation-cli-connector.py')
            #os.system("start cmd /k" + ' python ' +cmd)
            try:
                c=subprocess.check_call(['python', cmd,'-m',self.comboBox_model.currentText(),'-p',self.comboBox_port.currentText(),'-o',str(self.lineEdit_save_raw.text())], shell=True)
                self.updateProgressBar(c)
                if self.comboBox_model.currentText()=='':
                    self.textEdit.setText('insert port please!')
                if c!=0:
                    self.textEdit.setText('connessione fallita!')
            
                layer = QgsVectorLayer(str(self.lineEdit_save_raw.text()), 'totalopenstation', 'ogr')
                    
                layer.isValid() 

                
                QgsProject.instance().addMapLayer(layer)

                QMessageBox.warning(self, 'Total Open Station luncher',
                                          'data loaded into panel Layer', QMessageBox.Ok)
            
                self.progressBar.reset()
                r=open(str(self.lineEdit_save_raw.text()),'r')
                lines = r.read().split(',')
                self.textEdit.setText(str(lines))
            
            except:
                pass
        
        
