import yadisk
import os
from PIL import Image
import requests
from urllib.parse import urlparse, parse_qs
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

CLIENT_ID = "23cfcbc5a2234eb0b635a3f6b6c7ad3e"
CLIENT_SECRET = "9436c471a48e426d81eb20aa680462f1"
REDIRECT_URI = "http://localhost:8000/oauth/callback"

y = yadisk.YaDisk()


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_components = parse_qs(urlparse(self.path).query)
        if "code" in query_components:
            self.server.auth_code = query_components["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization failed!")


def get_oauth_token():
    auth_url = f"https://oauth.yandex.ru/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    print(f"Open this URL in your browser to authorize the application: {auth_url}")
    webbrowser.open(auth_url)

    server = HTTPServer(('localhost', 8000), OAuthHandler)
    server.handle_request()

    auth_code = server.auth_code
    token_response = requests.post(
        "https://oauth.yandex.ru/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI
        }
    )
    token_response_data = token_response.json()
    return token_response_data["access_token"]


def list_all_items_in_public_folder(public_url):
    public_meta = y.get_public_meta(public_url)
    folders = []
    if 'embedded' in public_meta and 'items' in public_meta['embedded']:
        for index, item in enumerate(public_meta['embedded']['items']):
            if item['type'] == 'dir':
                print(f"{index + 1}. {item['name']}")
                folders.append(item)
    else:
        print("No items found in the public folder.")
    return folders


def download_images_from_folder(public_key, folder_path, download_path="images"):
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    folder_meta = y.get_public_meta(public_key, path=folder_path)
    if 'embedded' in folder_meta and 'items' in folder_meta['embedded']:
        for file_item in folder_meta['embedded']['items']:
            if file_item['type'] == 'file' and file_item['name'].lower().endswith(('png', 'jpg', 'jpeg')):
                file_path = os.path.join(download_path, file_item['name'])
                y.download_public(public_key, file_path, path=file_item['path'])
                print(f"Downloaded: {file_item['name']}")
    else:
        print(f"No images found in the folder {folder_path}.")


def create_tiff_from_images(image_folder, output_file):
    images = []
    for file_name in os.listdir(image_folder):
        if file_name.lower().endswith(('png', 'jpg', 'jpeg')):
            image_path = os.path.join(image_folder, file_name)
            try:
                img = Image.open(image_path)
                images.append(img)
            except (IOError, Image.DecompressionBombError) as e:
                print(f"Cannot open image file {image_path}: {e}")

    if images:
        images[0].save(output_file, save_all=True, append_images=images[1:], compression='tiff_deflate')
        print(f"TIFF file created: {output_file}")
    else:
        print("No images found to create TIFF file.")


if __name__ == "__main__":
    token = get_oauth_token()
    y.token = token

    public_url = 'https://disk.yandex.ru/d/V47MEP5hZ3U1kg'

    print("Список всех папок в публичной папке:")
    folders = list_all_items_in_public_folder(public_url)

    folder_index = int(input("Введите номер папки: ")) - 1
    if 0 <= folder_index < len(folders):
        selected_folder = folders[folder_index]
        download_images_from_folder(public_url, selected_folder['path'])

        image_folder = "images"
        output_file = "Result.tif"
        create_tiff_from_images(image_folder, output_file)
    else:
        print("Неверный номер папки.")
