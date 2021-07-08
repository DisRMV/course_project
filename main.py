import json
import time
import requests
from progress.bar import IncrementalBar


class VkLoader:
    def __init__(self, token, version=5.131):
        self.token = token
        self.v = version

    def get_photos(self, owner_id, album='profile', count=5):
        """Valid values for the parameter 'album' are 'profile', 'wall', 'saved'"""
        url = 'https://api.vk.com/method/photos.get'
        params = {
                  'access_token': self.token, 'v': self.v, 'owner_id': owner_id,
                  'album_id': album, 'extended': 1, 'count': count
                 }
        response = requests.get(url, params)
        return response.json()

    def upload_dict(self, owner_id, album='profile', count=5):
        result = {}
        response = self.get_photos(owner_id, album, count)
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

    def create_catalog(self, catalog_name='Uploaded files'):
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = {'Authorization': f'OAuth {self.token}'}
        response = requests.put(url, headers=headers, params={'path': catalog_name})
        return response.status_code

    def upload_photos(self, upload_dict, catalog_name='Uploaded files'):
        bar = IncrementalBar('Processing', max=len(upload_dict))
        result = []
        self.create_catalog(catalog_name)
        url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        headers = {'Authorization': f'OAuth {self.token}'}
        for k, v in upload_dict.items():
            params = {'path': f'{catalog_name}/{k}.jpg', 'url': v[0]}
            requests.post(url=url, headers=headers, params=params)
            result.append({'file_name': f"{k}.jpg", 'size': v[1]})
            bar.next()
        bar.finish()
        with open('result.json', 'w', encoding='utf-8') as file:
            json.dump(result, file)
        return result


if __name__ == '__main__':
    vk_instance = VkLoader('ВК токен')
    vk_upload_dict = vk_instance.upload_dict('чей-нибудь id')
    ya_instance = YaUploader('Яндекс токен')
    ya_instance.upload_photos(vk_upload_dict)
