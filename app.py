from flask import Flask, render_template, request, send_file, jsonify
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests
import hashlib
import shutil
import zipfile

app = Flask(__name__)

def create_directory(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

def generate_filename(url):
    name = os.path.basename(urlparse(url).path) or "index"
    return f"{name}_{hashlib.md5(url.encode()).hexdigest()[:8]}"

def download_file(url, folder):
    try:
        local_filename = os.path.join(folder, generate_filename(url))
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with open(local_filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
        return local_filename
    except requests.exceptions.RequestException as e:
        return None

def clone_website(url, output_dir):
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        create_directory(output_dir)

        # Save the HTML
        with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as file:
            file.write(soup.prettify())

        # Download CSS, JS, and images
        for tag, folder in [("link", "css"), ("script", "js"), ("img", "images")]:
            for element in soup.find_all(tag):
                attr = "href" if tag == "link" else "src"
                if element.has_attr(attr):
                    file_url = urljoin(url, element[attr])
                    create_directory(os.path.join(output_dir, folder))
                    download_file(file_url, os.path.join(output_dir, folder))

        return True
    except Exception as e:
        return False

def zip_folder(folder_path, zip_name):
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/clone", methods=["POST"])
def clone():
    url = request.form["url"]
    user_path = request.form["path"]

    if not os.path.exists(user_path):
        os.makedirs(user_path)

    output_dir = os.path.join(user_path, "cloned_site")
    zip_path = os.path.join(user_path, "cloned_site.zip")

    success = clone_website(url, output_dir)
    if success:
        zip_folder(output_dir, zip_path)
        shutil.rmtree(output_dir)  # Clean up folder after zipping
        return send_file(zip_path, as_attachment=True)
    else:
        return jsonify({"message": "Try again! Website not cloned due to an issue."}), 400

if __name__ == "__main__":
    app.run(debug=True)
