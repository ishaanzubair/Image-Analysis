import os
import time
from google.cloud import storage
from flask import Flask, redirect, request, Response
import io
from PIL import Image
import json
import google.generativeai as genai

os.makedirs('files', exist_ok=True)

genai.configure(api_key=os.environ.get("GEMINI_API"))
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

PROMPT = "Give me one line title and description for this image in json format."

app = Flask(__name__)
storage_client = storage.Client()
Name_of_bucket = os.environ.get("My_Bucket")

@app.get("/hello")
def hello():
    who = request.args.get("who", default="World")
    time.sleep(5)
    return f"Hello {who}!\n"

@app.route('/')
def index():
    index_html = """
    <html lang="en">
    <head>
      <title>Image Upload</title>
      <style>
        body {
          font-family: 'Segoe UI', sans-serif;
          background-color: #20e884;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 40px;
          margin: 0;
        }
        .container {
          background: white;
          padding: 30px;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          max-width: 500px;
          width: 100%;
        }
        h3 {
          margin-top: 40px;
          font-size: 1.2rem;
        }
        form div {
          margin-bottom: 15px;
        }
        input[type="file"] {
          width: 100%;
          padding: 10px;
          border: 1px solid #ccc;
          border-radius: 6px;
        }
        button {
          background-color: #20e884;
          color: white;
          border: none;
          padding: 10px 20px;
          font-size: 16px;
          border-radius: 6px;
          cursor: pointer;
          transition: background 0.3s ease;
        }
        button:hover {
          background-color: #0056b3;
        }
        ul {
          list-style: none;
          padding: 0;
          max-width: 500px;
          width: 100%;
        }
        li {
          margin: 8px 0;
        }
        a {
          text-decoration: none;
          color: #333;
          font-weight: 500;
        }
        a:hover {
          text-decoration: underline;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h2>Upload an Image</h2>
        <form method="post" enctype="multipart/form-data" action="/upload">
          <div>
            <label for="file">Choose a JPEG file:</label>
            <input type="file" id="file" name="form_file" accept="image/jpeg"/>
          </div>
          <div>
            <button type="submit">Upload</button>
          </div>
        </form>
      </div>
      <h3>Uploaded Files:</h3>
      <ul>
    """
    uploaded_files = list_files()
    for file in uploaded_files:
        index_html += f'<li><a href="/files/{file.name}">{file.name}</a></li>'
    index_html += "</ul></body></html>"
    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['form_file']
    bucket = storage_client.bucket(Name_of_bucket)
    blob_image = bucket.blob(file.filename)
    blob_image.upload_from_file(file_obj=file, rewind=True)
    file.save(os.path.join("", file.filename))
    response = model.generate_content([Image.open(file), PROMPT])
    left_index = response.text.index("{")
    right_index = response.text.index("}")
    response_string = response.text[left_index:right_index + 1]
    json_response = json.loads(response_string)
    file_name = file.filename.split(".")[0] + ".json"
    with open(file_name, "w") as json_file:
        json.dump(json_response, json_file, indent=4)
    blob_text = bucket.blob(file_name)
    blob_text.upload_from_filename(file_name)
    return redirect("/")

@app.route('/files')
def list_files():
    files = storage_client.list_blobs(Name_of_bucket)
    jpegs = []
    for file in files:
        if file.name.lower().endswith(".jpeg") or file.name.lower().endswith(".jpg"):
            jpegs.append(file)
    return jpegs

@app.route('/files/<filename>')
def get_file(filename):
    bucket = storage_client.bucket(Name_of_bucket)
    blob = bucket.blob(filename.split(".")[0] + ".json")
    file_data = blob.download_as_bytes()
    file_data = json.loads(file_data.decode('utf-8'))
    html = f""" 
    <html>
    <head>
      <style>
        body {{
          font-family: 'Segoe UI', sans-serif;
          background-color: #20e884;
          text-align: center;
          padding: 40px;
        }}
        img {{
          max-width: 80%;
          height: auto;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        h2 {{
          margin-top: 20px;
        }}
        p {{
          font-size: 1.1rem;
          color: crimson;
        }}
      </style>
    </head>
    <body>
      <img src='/images/{filename}'>
      <h2>Title: {file_data['title']}</h2>
      <p>Description: {file_data['description']}</p>
    </body>
    </html>
    """
    return html

@app.route('/images/<imagename>')
def view_image(imagename):
    bucket = storage_client.bucket(Name_of_bucket)
    blob = bucket.blob(imagename)
    file_data = blob.download_as_bytes()
    return Response(io.BytesIO(file_data), mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=True)
