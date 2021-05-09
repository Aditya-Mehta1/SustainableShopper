import os
import BarcodeReader

def AutomateScraping(barcode_number):
    directory = r'/Users/aditya/Desktop/Amazon_Html'
    for filename in os.listdir(directory):
        if filename.endswith(".html"):
            filename = directory + "/" + filename
            BarcodeReader.search_sustainability(BarcodeReader.search_other_stuff(filename,barcode_number))

