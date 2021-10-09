import sys
import csv
import datetime
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QDialog, QMessageBox, QPushButton, QTableView, QLabel, QFileDialog, QProgressDialog, QApplication
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel
from PyQt5.QtCore import QFile, QIODevice, QFileInfo, QDir, Qt
from PyQt5.QtGui import QPixmap, QIcon
from fpdf import FPDF

from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np
from tensorflow.keras.models import load_model
import time

# from tensorflow.python.keras.backend import equal

import resources


def createConnection():
    db_image = QSqlDatabase.addDatabase('QSQLITE')
    db_image.setDatabaseName(':memory:')
    query = QSqlQuery(db_image)
    if not db_image.open():
        QMessageBox.critical(None, "Tidak Dapat Membuka Database!",
                "Koneksi ke Database tidak dapat dilakukan.\n"
                "Program membutuhkan support SQLite.\n\n "
                "Click Cancel untuk keluar.",
                QMessageBox.Cancel)
        return False
    query.exec_('''
    CREATE TABLE IF NOT EXISTS imgTable (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
        filename TEXT, 
        imagedata BLOB, 
        filepath TEXT, 
        classification TEXT, 
        date TEXT);''')

    print("Diterima Koneksi ke database:\n", db_image.tables())
    return True


def clearDbImage(kode):
    if kode == 'DELETEALL':
        query = QSqlQuery()
        query.exec_('''DELETE FROM imgTable''')
        query.exec_('''DELETE FROM sqlite_sequence where name='imgTable';''')


class WindowKlasifikasi(QDialog):
    def __init__(self, *args, **kwargs):
        super(WindowKlasifikasi, self, *args, **kwargs).__init__()

        self.BAHASA = 0

        fileh = QFile(':/ui/klasifikasi.ui')
        fileh.open(QFile.ReadOnly)
        loadUi(fileh, self)
        fileh.close

        self.button = self.findChild(QPushButton, "pushButtonPilihCitraKlasifikasi")
        self.button.clicked.connect(self.load_image)

        self.model = QSqlTableModel()
        self.model.setTable("imgTable")
        self.model.select()

        self.model.setHeaderData(1, Qt.Horizontal, "Nama File")
        self.model.setHeaderData(4, Qt.Horizontal, "Hasil Klasifikasi")
        
        self.table = self.findChild(QTableView, "tableViewKlasifikasi")
        self.table.setModel(self.model)
        self.table.hideColumn(0)
        self.table.hideColumn(2)
        self.table.hideColumn(3)
        self.table.hideColumn(5)
        self.table.resizeColumnsToContents()
        self.table.clicked.connect(self.onTableClicked)

        self.label = self.findChild(QLabel, "labelDisplayCTKlasifikasi")
        self.labelKlasifikasi = self.findChild(QLabel, "labelHasilKlasifikasi")
        self.labelNama = self.findChild(QLabel, "labelNamaFile")

        self.button2 = self.findChild(QPushButton, "pushButtonResetKlasifikasi")
        self.button2.clicked.connect(self.resetTabelImage)
        
        self.button3 = self.findChild(QPushButton, "pushButtonJalankanKlasifikasi")
        self.button3.clicked.connect(self.jalankanKlasifikasi)

        self.button4 = self.findChild(QPushButton, "pushButtonSimpanCsv")
        self.button4.clicked.connect(self.simpanHasilCsv)

        self.button5 = self.findChild(QPushButton, "pushButtonSimpanPdf")
        self.button5.clicked.connect(self.simpanHasilPdf)

        self.button6 = self.findChild(QPushButton, "pushButtonPetunjuk")
        self.button6.clicked.connect(self.bukaPetunjuk)
        self.windowPetunjuk = None

        self.button7 = self.findChild(QPushButton, "pushButtonBahasa")
        self.button7.clicked.connect(self.gantiBahasa)

    def gantiBahasa(self):
        if self.BAHASA is 0:
            self.BAHASA = 1
            self.model.setHeaderData(1, Qt.Horizontal, "File Name")
            self.model.setHeaderData(4, Qt.Horizontal, "Classification Result")
            self.table.resizeColumnsToContents()
            self.button.setText("Choose Image")
            self.button3.setText("Run Classification")
            self.button4.setText("Save CSV")
            self.button5.setText("Save PDF")
            self.button6.setText("User Guide")
            self.button7.setStyleSheet("border-image: url(:/image/indonesian.png);")
            self.labelKlasifikasi.setText("<< Classification Result >>")
            self.labelNama.setText("File Name")

        else:
            self.BAHASA = 0
            self.model.setHeaderData(1, Qt.Horizontal, "Nama File")
            self.model.setHeaderData(4, Qt.Horizontal, "Hasil Klasifikasi")
            self.table.resizeColumnsToContents()
            self.button.setText("Pilih Citra")
            self.button3.setText("Jalankan Klasifikasi")
            self.button4.setText("Simpan CSV")
            self.button5.setText("Simpan PDF")
            self.button6.setText("Petunjuk Pemakaian")
            self.button7.setStyleSheet("border-image: url(:/image/english.png);")
            self.labelKlasifikasi.setText("<< Hasil Klasifikasi >>")
            self.labelNama.setText("Nama File")

    def onTableClicked(self, index):
        if index.isValid:
            row = index.row()
            ix = self.table.model().index(row, 2)
            pix = QPixmap()
            pix.loadFromData(ix.data())
            self.label.setPixmap(pix)

            query = QSqlQuery()
            if query.exec_(f'''SELECT id, filename, classification FROM imgTable WHERE id = {row+1};'''):
                query.first()
                self.labelNama.setText(query.value(1))
                if query.value(2):
                    print('Dipilih klasifikasi', query.value(0), query.value(1))
                    self.labelKlasifikasi.setText(query.value(2))
                else:
                    if self.BAHASA is 0:
                        self.labelKlasifikasi.setText("<< Hasil Klasifikasi >>")
                    else:
                        self.labelKlasifikasi.setText("<< Classification Result >>")

    def load_image(self):
        imgList = QFileDialog.getOpenFileNames(self, 'Select one or more files to open', QDir.currentPath(), "Images (*.jpg *.png)")
        print(imgList)
        imgs, _ = imgList
        print(imgs)
        for fname in imgs:
            if fname:
                self.saveImage(fname)

    def saveImage(self, filepath):
        file = QFile(filepath)
        if not file.open(QIODevice.ReadOnly):
            return
        ba = file.readAll()
        name = QFileInfo(filepath).fileName()
        record = self.model.record()
        record.setValue("filename", name)
        record.setValue("imagedata", ba)
        record.setValue("filepath", filepath)

        if self.model.insertRecord(-1, record):
            self.model.select()

    def resetTabelImage(self):
        clearDbImage('DELETEALL')
        self.model.select()
        if self.BAHASA is 0:
            self.labelKlasifikasi.setText("<< Hasil Klasifikasi >>")
            self.labelNama.setText("Nama File")
            default_img = QPixmap(':/image/preview.png')
        else:
            self.labelKlasifikasi.setText("<< Classification Result >>")
            self.labelNama.setText("File Name")
            default_img = QPixmap(':/image/preview.png')
        self.label.setPixmap(default_img)

    def get_img_resize(self, path):
        '''
        Mengambil citra dari path yang disediakan,
        kemudian dilakukan Normalisasi dan Standardisasi

        input   : path citra, jpg atau png
        output  : numpy array dari citra yang sudah dipreprocessing
                shape - (1,224,224,3)
        '''
        #Load Image
        img         = img_to_array(load_img(path, color_mode='rgb', target_size=(224,224)))

        #Load mean and std from training dataset
        mean        = np.load('model/mean_per_channel_train_fold_5.npy')

        std         = np.load('model/std_per_channel_train_fold_5.npy')

        #Normalization and Standardization
        img_input   = (img-mean)/std

        return np.array([img_input])

    def get_proba(self, img_array, debug=False):

        '''
        Load model yang ada, kemudian melakukan prediksi

        input  : array citra dengan dimensi (1,224,224,3)
        output : Array Probabilitas klasifikasi dengan dimensi (1,2) -> [[Proba Negatif, Proba Positif]]
        '''
        if debug:
            t = time.time()

        #load Model
        model = load_model('model/ResNet50_ReFold_5_40.h5')
        # model = load_model('model/ResNet50_fold_3.h5')

        #Probabilitas hasil prediksi
        proba = model.predict(img_array)

        if debug:
            duration = time.time() - t
            print("Klasifikasi membutuhkan waktu " + str(duration) + "detik")

        return proba

    def proba_to_class(self, proba_arr):

        '''
        Konversi hasil array probabilitas hasil prediksi model ke kategori Negatif atau Positif

        input  : array probabilitas dengan dimensi (1,2)
        output : String Positif atau Negatif dan persentasenya
        '''

        print(proba_arr[0])
        if proba_arr[0][0] == proba_arr[0][1]:
            return 'NA'

        class_dict = {0:'Negatif (Negative)', 1:'Positif (Positive)'}
        index = np.argmax(proba_arr)

        return class_dict[index]+': {:.2%}'.format(proba_arr[0][index])

    def jalankanKlasifikasi(self):
        query = QSqlQuery()
        query_up = QSqlQuery()

        if query.exec('''SELECT id FROM imgTable'''):
            query.last()
            numFiles = query.value(0)
            if isinstance(numFiles, int):
                t = time.time()
                if self.BAHASA is 0:
                    progress = QProgressDialog("Model sedang melakukan klasifikasi...", "Hentikan Proses", 0, numFiles, self)
                else:
                    progress = QProgressDialog("Model is working...", "Stop the Process", 0, numFiles, self)
                progress.setWindowModality(Qt.WindowModal)
                counter = 0

                query.exec_('''SELECT id, filepath FROM imgTable''')
                while query.next():
                    progress.setValue(counter)
                    counter+=1
                    if progress.wasCanceled():
                        break

                    current_image_id = query.value(0)
                    img_array = self.get_img_resize(query.value(1))
                    proba = self.get_proba(img_array, debug=True)
                    class_prec = self.proba_to_class(proba)
                    date = datetime.datetime.now()
                    print(class_prec, 'untuk id', current_image_id, 'pada', date)
                    query_up.exec_(f'''UPDATE imgTable SET classification = '{class_prec}', date = '{date}' WHERE id = {current_image_id};''')
                
                progress.setValue(numFiles)
                self.model.select()
                self.table.resizeColumnsToContents()
                
                query.exec_('''SELECT id, filename, classification, date FROM imgTable''')
                while query.next():
                    print(query.value(0), query.value(1), query.value(2), query.value(3))

                duration = time.time() - t
                print("Seluruh citra dapat diklasifikasikan dengan waktu " + str(duration) + "detik")

    def simpanHasilCsv(self):
        query = QSqlQuery()
        if query.exec_("SELECT id, filename, filepath, classification, date FROM imgTable;"):
            print("Exporting data into CSV............")
            date = datetime.datetime.now()
            day = date.strftime("%d")
            month = date.strftime("%m")
            year = date.strftime("%y")
            dirpath, ok = QFileDialog.getSaveFileName(self, "Save File", QDir.currentPath() + "/HasilKlasifikasi_" + day + month + year + ".csv", "CSV Files (*.csv)")
            if ok:
                with open(dirpath, "w") as csv_file:
                    csv_writer = csv.writer(csv_file, delimiter=",")
                    csv_writer.writerow(['ID', 'Nama File', 'Letak File', 'Hasil Klasifikasi', 'Tanggal Klasifikasi'])
                    while query.next():
                        id = query.value(0)
                        nama = query.value(1)
                        letak = query.value(2)
                        klasifikasi = query.value(3)
                        tanggal = query.value(4)
                        csv_writer.writerow([id, nama, letak, klasifikasi, tanggal])

                print(f"Data exported Successfully into {dirpath}")
                QMessageBox.information(None, "Data Klasifikasi Berhasil Disimpan!",
                    f"Data berhasil disimpan di {dirpath}.\n",
                    QMessageBox.Ok)

        else:
            QMessageBox.warning(None, "Data Klasifikasi Tidak Dapat Diambil!",
                "Terjadi kesalahan saat mengambil data dari database. Coba lagi.\n",
                QMessageBox.Ok)

    def simpanHasilPdf(self):
        query = QSqlQuery()
        if query.exec_("SELECT id, filename, filepath, classification, date FROM imgTable;"):
            print("Exporting data into PDF............")
            date = datetime.datetime.now()
            day = date.strftime("%d")
            month = date.strftime("%m")
            year = date.strftime("%y")
            dirpath, ok = QFileDialog.getSaveFileName(self, "Save File", QDir.currentPath() + "/HasilKlasifikasi_" + day + month + year + ".pdf", "PDF Files (*.pdf)")
            if ok:
                pdf = PDF()
                pdf.set_title("Hasil Klasifikasi COVID-19 dari Citra CT Paru-paru")
                pdf.alias_nb_pages()
                while query.next():
                    nama = query.value(1)
                    letak = query.value(2)
                    klasifikasi = query.value(3)
                    tanggal = query.value(4)
                    pdf.add_page()
                    pdf.set_font('Times', '', 12)
                    pdf.image(letak, None, None, 100)
                    pdf.ln(h = '')
                    pdf.cell(60, 10, "Nama File :", 0, 0)
                    pdf.cell(0, 10, nama, 0, 1)
                    pdf.cell(60, 10, "Letak File :", 0, 0)
                    pdf.cell(0, 10, letak, 0, 1)
                    pdf.cell(60, 10, "Hasil Klasifikasi :", 0, 0)
                    pdf.cell(0, 10, klasifikasi, 0, 1)
                    pdf.cell(60, 10, "Waktu Klasifikasi :", 0, 0)
                    pdf.cell(0, 10, tanggal, 0, 1)
                pdf.output(dirpath, 'F')

                print(f"Data exported Successfully into {dirpath}")
                QMessageBox.information(None, "Data Klasifikasi Berhasil Disimpan!",
                    f"Data berhasil disimpan di {dirpath}.\n",
                    QMessageBox.Ok)

        else:
            QMessageBox.warning(None, "Data Klasifikasi Tidak Dapat Diambil!",
                "Terjadi kesalahan saat mengambil data dari database. Coba lagi.\n",
                QMessageBox.Ok)

    def bukaPetunjuk(self):
        if self.windowPetunjuk is None:
            self.windowPetunjuk = WindowPetunjuk()
        self.windowPetunjuk.setWindowTitle("Petunjuk Pengguna Aplikasi COVID-19")
        self.windowPetunjuk.show()


class WindowPetunjuk(QDialog):
    def __init__(self, *args, **kwargs):
        super(WindowPetunjuk, self, *args, **kwargs).__init__()

        fileh = QFile(':/ui/petunjuk.ui')
        fileh.open(QFile.ReadOnly)
        loadUi(fileh, self)
        fileh.close


class PDF(FPDF):
    def header(self):
        # Logo
        self.image('resources/logo.png', 10, 8, 33)
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(80)
        # Title
        self.cell(60, 10, 'Hasil Klasifikasi', 1, 0, 'C')
        # Line break
        self.ln(50)

    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(':/image/logo.png'))
    if not createConnection():
        sys.exit(1)

    windowKlasifikasi = WindowKlasifikasi()
    windowKlasifikasi.setWindowTitle("Aplikasi Klasifikasi COVID-19")
    windowKlasifikasi.show()

    try:
        sys.exit(app.exec())
    except:
        clearDbImage('DELETEALL')
        print("Exiting")