import os
import time
from google.cloud import storage
from flask import Flask, redirect, request, send_file, Response, render_template_string
import io
from PIL import Image
os.makedirs('files', exist_ok=True)
import json
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API"))

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
#   generation_config=generation_config,
  # safety_settings = Adjust safety settings
  # See https://ai.google.dev/gemini-api/docs/safety-settings
)

PROMPT = "Give me one line title and description for this image in json format."

def upload_to_gemini(path, mime_type=None):
  """Uploads the given file to Gemini.

  See https://ai.google.dev/gemini-api/docs/prompting_with_media
  """
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  # print(file)
  return file


# print(response)
app = Flask(__name__)

storage_client = storage.Client()
Name_of_bucket = os.environ.get("My_Bucket")



@app.get("/hello")
def hello():
    """Return a friendly HTTP greeting."""
    who = request.args.get("who", default="World")
    time.sleep(5)
    return f"Hello {who}!\n"

@app.route('/')
def index():
    index_html = """
    <html lang="en">
    <head><title>File Upload</title></head>
    <body class="container py-5" style="background-color: blue;">
    <form method="post" enctype="multipart/form-data" action="/upload">
      <div>
        <label for="file">Choose file to upload</label>
        <input type="file" id="file" name="form_file" accept="image/jpeg"/>
      </div>
      <div>
        <button type="submit">Submit</button>
      </div>
    </form>
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

  


    #if 'form_file' not in request.files:
       # return "No file part", 400

    file = request.files['form_file']
    bucket = storage_client.bucket(Name_of_bucket)
    blob_image = bucket.blob(file.filename)
    blob_image.upload_from_file(file_obj=file, rewind=True)
    file.save(os.path.join("",file.filename))
    response = model.generate_content([Image.open(file), PROMPT])
    print(response.text)
    left_index=response.text.index("{")
    right_index=response.text.index("}")
    response_string=response.text[left_index:right_index+1]
    print (response_string,type(response_string))
    json_response=json.loads(response_string)
    print(json_response)
    file_name = file.filename.split(".")[0]+".json"

    #Write json data to a file
    with open(file_name, "w") as json_file:
      json.dump(json_response, json_file, indent=4)
    blob_text = bucket.blob(file.filename.split(".")[0]+".json")
    blob_text.upload_from_filename(file.filename.split(".")[0]+".json")

    return redirect("/")

@app.route('/files')
def list_files():
    """Return a list of image files in the Google Cloud Storage bucket."""
    files = storage_client.list_blobs(Name_of_bucket)
    jpegs = []
    for file in files:
      if file.name.lower().endswith(".jpeg") or file.name.lower().endswith(".jpg"):
        jpegs.append(file)

    return jpegs

@app.route('/files/<filename>')
def get_file(filename):
    """Download file from Google Cloud Storage and serve it."""
    bucket = storage_client.bucket(Name_of_bucket)
    blob = bucket.blob(filename.split(".")[0]+".json")
    file_data = blob.download_as_bytes()
    file_data = json.loads(file_data.decode('utf-8'))
    print(file_data)
    html= f"""
      <img src='/images/{filename}'>
      <h2>Title: {file_data['title']}</h2>
      <p style="color: crimson;">Description: {file_data['description']}</p>
    """
    return html  
# return Response(io.BytesIO(filedata), mimetype='image/jpeg')

@app.route('/images/<imagename>')
def view_image(imagename):
  bucket = storage_client.bucket(Name_of_bucket)
  blob = bucket.blob(imagename)
  file_data = blob.download_as_bytes()
  return Response(io.BytesIO(file_data), mimetype='image/jpeg')


if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=True)
