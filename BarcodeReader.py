from flask import Flask, redirect, url_for, render_template, Response, request
import cv2
from pyzbar import pyzbar
import bs4 as bs
import sqlite3
import os, ssl
import requests
import tkinter
from tkinter import *

barcode = 0

def search(barcode_number):
    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context
    url = "https://www.amazon.in/s?k=" + str(barcode_number)
    headers = {
        'authority': 'www.amazon.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'dnt': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-dest': 'document',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    }
    response = requests.get(url, headers = headers)
    source = response.text
    soup = bs.BeautifulSoup(source, 'html.parser')
    link = ''
    for links in soup.find_all('a'):
        link =  links.get('href')
        if link:
            if "keywords=" + str(barcode_number) in link:
                link = "amazon.in" + link
                break
    conn = sqlite3.connect('products.sqlite')
    cur = conn.cursor()
    cur.execute('INSERT INTO Products_To_Search(Barcode, Field2) VALUES(?,?)', (barcode_number, link))
    cur.close()
    conn.commit()

def search_other_stuff(path,barcode_number):
    file = open(path, "r")
    source = file.read()

    #Dictionary
    AllInformation = dict()
    AllInformation['Barcode Number'] = barcode_number
    AllInformation["Package Information"] = list()
    AllInformation["Materials"] = list()
    AllInformation["Ingredients"] = list()


    #List of materials to find
    Materials = ["cotton",
                "leather",
                "denim",
                "nylon",
                "polyester",
                "jute"
                "linen",
                "khadi",
                "wool",
                "acrylic",
                "alpaca",
                "carbon Fiber",
                "hemp"
                "elastane",
                "spandex",
                "flax fiber",
                "glass fiber",
                "silk"]

    # To find package information
    soup = bs.BeautifulSoup(source, 'html.parser')
    for trs in soup.find_all("tr",  attrs={}):
        ths = trs.find("th", attrs={"class": "a-color-secondary a-size-base prodDetSectionEntry"})
        if ths:
            if ths.text.strip() == "Package Information":
                print(trs.find("td").text.strip())
                AllInformation["Package Information"].append(trs.find("td").text.strip().lower())

    index = 0
    # To find materials
    desc = soup.find('div', attrs={"id": "feature-bullets"})
    if desc:
        info = desc.find_all('span')
        for tags in info:
            for material in Materials:
                if material in tags.text.lower():
                    information = tags.text.lower()
                    index = information.lower().index(material)
                    temp = information[:index]
                    percent = re.findall("[0-9]+%+", temp)[0]
                    information = information[index:]
                    AllInformation['Materials'].append((material, percent))


    # To find ingredients
    ImportantInformation = soup.find('div', attrs={"id":"important-information"})
    if ImportantInformation:
        Div = ImportantInformation.find('div')
        if Div:
            ps = Div.find_all('p')
            for p in ps:
                if p.text:
                    ingredients = p.text
                    ingredients = ingredients.replace(' ', '')
                    ingredient = ingredients.replace(',', ' ').split()
                    AllInformation['Ingredients'] = ingredient
    print(AllInformation)
    return AllInformation

def search_sustainability(AllInformation):
    conn = sqlite3.connect('products.sqlite')
    cur = conn.cursor()


    SustainablityScores = dict()
    SustainablityScores['Materials'] = list()
    SustainablityScores['Package Information'] = list()
    SustainablityScores['Ingredients'] = list()

    for (material,percent) in AllInformation["Materials"]:
        cur.execute('SELECT Field2 FROM Materials WHERE Textile = ?', (material, ))
        score = cur.fetchone()
        if score:
            SustainablityScores['Materials'].append((material,score[0],percent))

    for material in AllInformation["Package Information"]:
        cur.execute('SELECT Field2 FROM PackagingMaterial WHERE Material = ?', (material, ))
        score = cur.fetchone()
        if score:
            SustainablityScores['Package Information'].append((material, score[0]))

    for material in AllInformation["Ingredients"]:
        cur.execute('SELECT Name FROM Ingredients')
        all_materials = cur.fetchall()
        if (material, ) in all_materials:
            SustainablityScores['Ingredients'].append(material.lower())

    cur.close()
    print(SustainablityScores)

    """
    Scoring the product
    """

    i = 0
    sum_m = 0
    sum_p = 0
    sum_i = 0

    n = len(SustainablityScores['Materials'])
    if n!= 0:
        i = i + 1
        for (material, score, percent) in SustainablityScores['Materials']:
            percent = int(percent.strip().replace("%", ""))
            sum_m = sum_m + score*percent/100
        if sum_m < 100:
            sum_m = 1
        elif sum_m < 200:
            sum_m = 2
        else:
            sum_m = 3

    n = len(SustainablityScores['Package Information'])
    if n!= 0:
        i = i + 1
        for (material, score) in SustainablityScores['Package Information']:
            sum_p += score
        sum_p = sum_p/n

    n = len(SustainablityScores['Ingredients'])
    if n!= 0:
        i = i + 1
        sum_i =len(SustainablityScores['Ingredients'])
    if(i != 0):
        score = (sum_p + sum_m + sum_i)/i
    else:
        score = 0
    conn = sqlite3.connect('products.sqlite')
    cur = conn.cursor()
    cur.execute('INSERT INTO ProductsDB(Barcode, Score, Material, Packaging_Info, Ingredients) VALUES (?,?,?,?,?)', (AllInformation['Barcode Number'], score, ' '.join([str(elem) for elem in AllInformation['Materials']]), ' '.join([str(elem) for elem in AllInformation['Package Information']]), ' '.join([str(elem) for elem in AllInformation['Ingredients']])))
    cur.close()
    conn.commit()

def show(AllInformation):
    print(AllInformation)
    window = Tk()
    window.title('Your Score')
    scores = {
        0: "No information on this product is available.",
        1: "Low score. This is product is very sustainable!",
        2: "Medium score. There may be more sustainable alternatives...",
        3: "High score. Very Unsustainable. Please look for alternatives!"
    }
    score = AllInformation[1]
    Score = Label(window, text = "Score: " +str(scores[int(AllInformation[1])]), font = ("ArialBold", 30))
    Materials = (' '.join([str(elem) for elem in AllInformation[2]])).replace(')',"").replace('(','').replace('\'','')
    Packaging_Information =  (' '.join([str(elem) for elem in AllInformation[3]])).replace(')',"")
    Ingredients =  (' '.join([str(elem) for elem in AllInformation[4]])).replace(')',"")
    if len(Materials) == 0:
        Materials = "None"
    if len(Packaging_Information) == 0:
        Packaging_Information = "None"
    if len(Ingredients) == 0:
        Ingredients = "None"
    Materials = "Materials: " + Materials
    Packaging_Information = "Packaging Information: " + Packaging_Information
    Ingredients = "Ingredients: " + Ingredients
    Materials = Label(window, text = Materials, font = ("ArialBold", 30))
    Packaging_Information = Label(window, text = Packaging_Information, font = ("ArialBold", 30))
    Ingredients = Label(window, text = Ingredients, font = ("ArialBold", 30))
    if score ==1:
        name = 'Low.png'
    elif score == 2:
        name = 'Medium.png'
    else:
        name = 'High.png'
    Score.grid(row = 0, column = 0)
    Materials.grid(row = 1, column = 0)
    Packaging_Information.grid(row = 2, column = 0)
    Ingredients.grid(row = 3, column = 0)
    window.mainloop()

def ShowFromUserInput(barcode, material_input, packaginginformation, ingredients):
    #Dictionary
    AllInformation = dict()
    AllInformation['Barcode Number'] = barcode
    AllInformation["Package Information"] = list()
    AllInformation["Materials"] = list()
    AllInformation["Ingredients"] = list()

    ingredients = ingredients.replace(' ', '')
    AllInformation['Ingredients'] = ingredients.replace(',', ' ').split()

    #List of materials to find
    Materials = ["cotton",
                "leather",
                "denim",
                "nylon",
                "polyester",
                "jute"
                "linen",
                "khadi",
                "wool",
                "acrylic",
                "alpaca",
                "carbon Fiber",
                "hemp"
                "elastane",
                "spandex",
                "flax fiber",
                "glass fiber",
                "silk"]

    for material in Materials:
                if material in material_input.lower():
                    information = material_input.lower()
                    index = information.lower().index(material)
                    temp = information[:index]
                    percent = re.findall("[0-9]+%+", temp)[0]
                    information = information[index:]
                    AllInformation['Materials'].append((material, percent))

    AllInformation["Package Information"].append(packaginginformation.lower())
    search_sustainability(AllInformation)
    FinalOutput(barcode)

def AlternateUserInput(barcode):
    window = Tk()
    l1 = Label(window, text = "To still get the score, please follow these steps", font = ("ArialBold", 15))
    l2 = Label(window, text = "Search your product barcode (" + str(barcode) + ") on Amazon.in" , font = ("ArialBold", 15))
    l3 = Label(window, text = "From the product page enter the following information: (If nothing found leave blank)" , font = ("ArialBold", 15))
    l4 = Label(window, text = "Material" , font = ("ArialBold", 15))
    l5 = Label(window, text = "Packaging Information" , font = ("ArialBold", 15))
    l6 = Label(window, text = "Ingredients" , font = ("ArialBold", 15))

    Material = Entry(window, width = 40)
    PackagingInformation = Entry(window, width = 40)
    Ingredients = Entry(window, width = 40)

    bt = Button (window, text= "Enter", command = lambda: ShowFromUserInput(barcode, Material.get(), PackagingInformation.get(), Ingredients.get()))
    l1.grid(row = 0, column = 0)
    l2.grid(row = 1, column = 0)
    l3.grid(row = 2, column = 0)
    l4.grid(row = 3, column = 0)
    Material.grid(row = 3, column = 1)
    l5.grid(row = 4, column = 0)
    PackagingInformation.grid(row = 4, column = 1)
    l6.grid(row = 5, column = 0)
    Ingredients.grid(row = 5, column = 1)
    bt.grid(row = 6, column = 0)
    window.mainloop()

def show_fail(barcode):
    print('check')
    window = Tk()
    print('check')
    window.title('Error')
    l1 = Label(window, text = "Sorry, barcode item " + str(barcode) + "is not available in our database", font = ("ArialBold", 30))
    l2 = Label(window, text = "We will add it at the soonest...", font = ("ArialBold", 30))
    bt = Button (window, text= "Enter", command = lambda: AlternateUserInput(barcode))
    l1.grid(row = 0, column = 0)
    l2.grid(row = 1, column = 0)
    bt.grid(row = 2, column = 0)
    window.mainloop()

def FinalOutput(barcode):
    conn = sqlite3.connect('harmful_materials.sqlite')
    cur = conn.cursor()
    cur.execute('SELECT * FROM ProductsDB WHERE Barcode = ?', (barcode,))
    AllInformation= cur.fetchone()
    if AllInformation is None:
        search(barcode)
        show_fail(barcode)
    else:
        show(AllInformation)

def read_barcodes(frame):
    barcodes = pyzbar.decode(frame)
    #trying to find the barcode in the picture
    barcode_number = 0

    for barcode in barcodes:
        #Making a rectangle around the barcode if found
        x, y , w, h = barcode.rect
        #Decoding the value of the barcode
        barcode_number = barcode.data.decode('utf-8')
        #Showing the rectangle around detected barcode using open_cv
        cv2.rectangle(frame, (x, y),(x+w, y+h), (0, 255, 0), 2)

    return (frame, barcode_number)

def get_video():
    video_feed = cv2.VideoCapture(0)
    ret, frame = video_feed.read()
    while ret:
        ret, frame = video_feed.read()
        frames = read_barcodes(frame)
        frame = frames[0]
        barcode_number = frames[1]
        if barcode_number!=0:
            global barcode
            barcode = barcode_number
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



app = Flask(__name__)
@app.route("/", methods=["POST","GET"])
def home_page():
    if request.method == 'POST':
        return redirect(url_for("results_page", barcode = barcode))
    else:
        return render_template('index.html')
    #elif barcode != 0:


@app.route('/video_feed')
def video_feed():
    return Response(get_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/results-<barcode>")
def results_page(barcode):
    conn = sqlite3.connect('products.sqlite')
    cur = conn.cursor()
    cur.execute('SELECT * FROM ProductsDB WHERE Barcode = ?', (barcode,))
    AllInformation= cur.fetchone()
    if AllInformation is None:
        search(barcode)
        return render_template('results.html', success_or_fail1 ="fail",  barcode = barcode)
    scores = {
    0: "No information on this product is available.",
    1: "Low score. This is product is very sustainable!",
    2: "Medium score. There may be more sustainable alternatives...",
    3: "High score. Very Unsustainable. Please look for alternatives!"}
    score_n = int(AllInformation[1])
    score = str(scores[score_n])
    Materials = (' '.join([str(elem) for elem in AllInformation[2]])).replace(')',"").replace('(','').replace('\'','')
    Packaging_Information =  (' '.join([str(elem) for elem in AllInformation[3]])).replace(')',"")
    Ingredients =  (' '.join([str(elem) for elem in AllInformation[4]])).replace(')',"")
    if len(Materials) == 0:
        Materials = "None"
    if len(Packaging_Information) == 0:
        Packaging_Information = "None"
    if len(Ingredients) == 0:
        Ingredients = "None"
    print(score_n)
    if score_n == 0:
        name = 'fail'
    elif score_n ==1:
        name = url_for('static', filename='images/Low.png')
    elif score_n == 2:
        name = url_for('static', filename='images/Medium.png')
    else:
         name = url_for('static', filename='images/High.png')
    return render_template('results.html', barcode = barcode, success_or_fail2 ="fail", score=score, Materials= Materials, Packaging_Type= Packaging_Information, Ingredients = Ingredients, name = name)

@app.route("/User_input-<barcode>", methods=["POST","GET"])
def User_input(barcode):
    if request.method == "POST":
        Material = request.form['Material']
        Packaging_Type = request.form['Packaging Type']
        Ingredients = request.form['Ingredients']
        AllInformation = dict()
        AllInformation['Barcode Number'] = barcode
        AllInformation["Package Information"] = list()
        AllInformation["Materials"] = list()
        AllInformation["Ingredients"] = list()

        Ingredients = Ingredients.replace(' ', '')
        AllInformation['Ingredients'] = Ingredients.replace(',', ' ').split()

        #List of materials to find
        Materials = ["cotton",
                    "leather",
                    "denim",
                    "nylon",
                    "polyester",
                    "jute"
                    "linen",
                    "khadi",
                    "wool",
                    "acrylic",
                    "alpaca",
                    "carbon Fiber",
                    "hemp"
                    "elastane",
                    "spandex",
                    "flax fiber",
                    "glass fiber",
                    "silk"]

        for material in Materials:
                    if material in Material.lower():
                        information = Material.lower()
                        index = information.lower().index(material)
                        temp = information[:index]
                        percent = "100%"
                        try:
                            percent = re.findall("[0-9]+%+", temp)[0]
                        except IndexError:
                            pass
                        information = information[index:]
                        AllInformation['Materials'].append((material, percent))

        AllInformation["Package Information"].append(Packaging_Type.lower())
        search_sustainability(AllInformation)
        return redirect(url_for("results_page", barcode = barcode))
    else:
        return render_template('User_input.html', barcode = barcode)

if __name__ == '__main__':
    app.run(debug=True)
