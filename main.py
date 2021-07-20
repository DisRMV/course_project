import json
import os
import time
import requests
import shutil
from progress.bar import IncrementalBar
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build


class VkLoader:
    def __init__(self, token):
        self.token = token

    def get_photos(self, owner_id, album='profile', count=5, version=5.131):
        """Valid values for the parameter 'album' are 'profile', 'wall', 'saved'"""
        url = 'https://api.vk.com/method/photos.get'
        params = {
                  'access_token': self.token, 'v': version, 'owner_id': owner_id,
                  'album_id': album, 'extended': 1, 'count': count
                 }
        response = requests.get(url, params)
        return response.json() if response.ok else response.status_code

    def download_photos(self, photos_d, folder_path='download'):
        os.mkdir(folder_path)
        for k, v in photos_d.items():
            with open(f'download/{str(k)}', 'wb') as file:
                response = requests.get(v[0])
                file.write(response.content)

    def remove_folder(self, folder_name='download'):
        shutil.rmtree(folder_name, ignore_errors=True)

    def upload_dict(self, response_d):
        """Return a dict that is used as an argument in method 'upload_photos' of class YaUploader and
            'upload_files' of class GoogleUploader"""
        result = {}
        response = response_d
        for i in response['response']['items']:
            sizes = sorted(i['sizes'], key=lambda size: size['height'] + size['width'])
            if i['likes']['count'] in result:
                key = f"{i['likes']['count']}, {time.strftime('%d_%m_%Y', time.localtime(int(i['date'])))}"
                result.update([(key, [sizes[-1]['url'], sizes[-1]['type']])])
            else:
                result.update([(i['likes']['count'], [sizes[-1]['url'], sizes[-1]['type']])])
        return result


class YaUploader:
    def __init__(self, token):
        self.token = token

    def get_headers(self):
        return {'Authorization': f'OAuth {self.token}'}

    def create_catalog(self, catalog_name='Uploaded files'):
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        response = requests.put(url, headers=self.get_headers(), params={'path': catalog_name})
        return response.status_code

    def upload_photos(self, upload_dict, catalog_name='Uploaded files'):
        bar = IncrementalBar('Processing', max=len(upload_dict))
        result = []
        self.create_catalog(catalog_name)
        url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        for k, v in upload_dict.items():
            params = {'path': f'{catalog_name}/{k}.jpg', 'url': v[0]}
            requests.post(url=url, headers=self.get_headers(), params=params)
            result.append({'file_name': f"{k}.jpg", 'size': v[1]})
            bar.next()
        bar.finish()
        with open('result.json', 'w', encoding='utf-8') as file:
            json.dump(result, file)
        return result


class GoogleUploader:

    def __init__(self):
        pass

    def get_auth(self, service_acc='service_acc.json', scopes='https://www.googleapis.com/auth/drive'):
        """Create an object you need to work with api"""
        credentials = service_account.Credentials.from_service_account_file(service_acc, scopes=[].append(scopes))
        service = build('drive', 'v3', credentials=credentials)
        return service

    def create_folder(self, folder_name, parent_id=None):
        """Create a folder on Drive, returns the newly created folders ID"""
        file_metadata = {'name': folder_name, 'mimeType': "application/vnd.google-apps.folder"}
        if parent_id:
            file_metadata['parents'] = [parent_id]
        root_folder = self.get_auth().files().create(body=file_metadata, fields='id').execute()
        return root_folder['id']

    def upload_files(self, folder_id, upload_dict):
        result = []
        bar = IncrementalBar('Processing', max=len(upload_dict))
        for k, v in upload_dict.items():
            name = f'{k}.jpg'
            file_path = f'download/{str(k)}'
            file_metadata = {'name': name, 'parents': [folder_id]}
            media = MediaFileUpload(file_path, resumable=True)
            self.get_auth().files().create(body=file_metadata, media_body=media, fields='id').execute()
            result.append({'file_name': f"{k}.jpg", 'size': v[1]})
            bar.next()
        bar.finish()
        with open('result.json', 'w', encoding='utf-8') as file:
            json.dump(result, file)
        return result


if __name__ == '__main__':
    vk_instance = VkLoader(os.getenv('VK_TOKEN'))
    response_dict = vk_instance.get_photos('VK_ID')
    vk_upload_dict = vk_instance.upload_dict(response_dict)
    vk_instance.download_photos(vk_upload_dict)

    ya_instance = YaUploader(os.getenv('YA_TOKEN'))
    ya_instance.upload_photos(vk_upload_dict)

    gd_instance = GoogleUploader()
    gd_folder = gd_instance.create_folder(folder_name='Uploaded files')
    gd_instance.upload_files(gd_folder, vk_upload_dict)

    vk_instance.remove_folder()
