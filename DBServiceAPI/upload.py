from flask import Flask, render_template, request,abort
from Dir_MyClasses.oracle_class import OracleUtils
import os

app = Flask(__name__, template_folder='Dir_Html_Templates')

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def upload_file():
    return render_template('upload.html')

# ფაილის მიღება და მონაცემთა ბაზაში ჩაწერა
@app.route('/upload', methods=['POST'])
def upload_exel():
    file = request.files['file'] # პირველი პარამეტრი POST ფორმიდან

    if file.filename == '':
        return "No selected file"

    

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)  # ფაილის შენახვა დირექტორიაში
    
    OrcUtil_F = OracleUtils()
    OrcUtil_F.create_table_from_data(file_path)  # ვიძახებთ upload_and_insert() ფუნქციას

    return f"File has been uploaded successfully: {file_path}"

    


   
    #return f"Received param_file : {param_file}"

    


if __name__ == '__main__':

    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True, host='192.168.54.11', port=8081)