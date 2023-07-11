import os,os.path
from flask import Flask, render_template, request, flash,redirect,url_for,send_file
from werkzeug.utils import secure_filename
import PyPDF2
import pymongo 
import bson.json_util as json_util
from datetime import datetime
from bson.objectid import ObjectId
# routing flask
app = Flask(__name__)
app.secret_key = "secret key"

UPLOAD_FOLDER = 'static/assets/isi'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["mongodbVSCodePlaygroundDB"]
mycol = mydb["filedata"]



def extract_text_from_pdf(pdf_file):
    """Extracts text from a PDF file"""
    pdf_reader = PyPDF2.PdfFileReader(pdf_file, strict=False) 
    count = pdf_reader.numPages
    output = ''
    for i in range(count):
        page = pdf_reader.getPage(i)
        output += page.extractText()
    return output


def save_file_to_db(file, output):
    """Saves file data to MongoDB"""
    filename = file.filename
    file_size = os.path.getsize(os.path.join(UPLOAD_FOLDER, secure_filename(file.filename)))
    file_url = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file_type = file.content_type
    print(filename)
    # Save file data to MongoDB
    mycol.insert_many([{
        "data" : output,
        "filename" : filename,
        "file_size" : file_size,
        "file_url" : file_url,
        "file_type" : file_type,
    }])


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        
        files = request.files.getlist('file[]')
        
        for file in files:
            if file.filename == '':
                return redirect(url_for('upload'))
            # Save file to UPLOAD_FOLDER
            filenames = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filenames))
            
            # Extract text from file
            output = extract_text_from_pdf(file)
            
            # Save file data to DB
            save_file_to_db(file, output)
        
    return render_template('home.html')


@app.route('/',methods=['GET', 'POST'])
def home():

    if request.method == 'POST':
        w = request.form['search']
        x = mycol.find(
            {
            "$text": {"$search": w},
            },
            {
            "score": {"$meta": "textScore"}
            }
            ).sort([('score', {'$meta': 'textScore'}),( "filename", -1 )]).limit(5)
        # tanpa index
        print("-------------------without index-------------------")
        noindex = mycol.find({"data": {"$regex": w}}).explain()["executionStats"]
        print(noindex)

        # dengan index
        print("-------------------with index-------------------")
        y = mycol.find({
        "$text": {"$search": w}
        }).explain()["executionStats"]
        print (y)

        # flash
        flash(f'Hasil pencarian untuk kata kunci "{w}"')
        # ['executionStatsM']['executionTimeMillis']
        # print(len(list(x)[0]['data']))
        # return json_util.dumps(list(x)[0]['data'])
        
        return render_template('data.html', data=list(x))       
  
    # str(list(x))
    return render_template('data.html')
    

@app.route('/tambah', methods=['GET', 'POST'])
def tambah():
    combo = request.form.get('combo')
    weight = request.form.get('berat')
    
    # buat drop index
    mydb.filedata.drop_indexes()

    # buat index
    x = mydb.filedata.create_index([('data',"text")], 
    weights={ 
        'data': 10,
    })

    flash('Index berhasil dibuat')
    # print(mydb.customers.getIndexes())
    return render_template('index.html')


@app.route('/tambahindex', methods=['GET', 'POST'])
def tambahindex():
    doc=mycol.find_one()
    
    return render_template('index.html',data=doc)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mydb = myclient["mongodbVSCodePlaygroundDB"]
        mycol = mydb["admin"]
        username = request.form['username']
        password = request.form['password']
        x = mycol.find_one({"username":username, "password":password})
        if x != None:
            return redirect(url_for('tambahindex'))
        else:
            flash('Username atau Password salah')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/detail')
def detail():
    detail= request.args.get('detail')
    x = mycol.find_one({"_id":ObjectId(detail)})
    return render_template('detail.html',data=x)

@app.route('/download')
def download():
    a= request.args.get('a')
    b= 'static\\assets\isi\\'+a
    return send_file(b, as_attachment=True)


if __name__ == '__main__':
    app.run(
        host='localhost',
        port= 5000,
        debug= True)

