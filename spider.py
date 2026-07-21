import sqlite3
import urllib.error
import ssl
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.request import urlopen
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = sqlite3.connect('spider.sqlite')
cur = conn.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS Pages
    (id INTEGER PRIMARY KEY, url TEXT UNIQUE, html TEXT,
     error INTEGER, old_rank REAL, new_rank REAL)''')

cur.execute('''CREATE TABLE IF NOT EXISTS Links
    (from_id INTEGER, to_id INTEGER, UNIQUE(from_id, to_id))''')

cur.execute('''CREATE TABLE IF NOT EXISTS Webs (url TEXT UNIQUE)''')

starturl = input('Enter web url: ')
if len(starturl) < 1: 
    starturl = 'http://python-data.dr-chuck.net/'

if starturl.endswith('/'): 
    starturl = starturl[:-1]

web = starturl
if starturl.endswith('.htm') or starturl.endswith('.html'):
    pos = starturl.rfind('/')
    web = starturl[:pos]

if len(web) > 1:
    cur.execute('INSERT OR IGNORE INTO Webs (url) VALUES ( ? )', (web,))
    cur.execute('INSERT OR IGNORE INTO Pages (url, html, new_rank) VALUES ( ?, NULL, 1.0 )', (starturl,))
    conn.commit()

cur.execute('''SELECT url FROM Webs''')
webs = [str(row[0]) for row in cur]
print("Aktiv veb ünvanlar:", webs)

# AVTOMATİK DOMEN TƏYİNİ (Dırnaq və f-string səhvi düzəldildi)
parsed_start = urlparse(starturl)
target_domain = parsed_start.netloc
if target_domain.startswith('www.'):
    target_domain = target_domain[4:]
print(f"Hədəf domen: {target_domain}")

many = 0
while True:
    if many < 1:
        sval = input('How many pages: ')
        if len(sval) < 1: 
            break
        many = int(sval)
    many -= 1

    cur.execute('SELECT id, url FROM Pages WHERE html IS NULL AND error IS NULL ORDER BY RANDOM() LIMIT 1')
    try:
        row = cur.fetchone()
        if row is None:
            print('No unretrieved HTML pages found')
            many = 0
            break
        fromid = row[0]
        url = row[1]
    except Exception as e:
        print('Xəta baş verdi:', e)
        many = 0
        break

    print(fromid, url, end=' ')

    cur.execute('DELETE FROM Links WHERE from_id=?', (fromid,))
    try:
        document = urlopen(url, context=ctx)
        html = document.read()
        
        if document.getcode() != 200:
            print("Error on page: ", document.getcode())
            cur.execute('UPDATE Pages SET error=? WHERE url=?', (document.getcode(), url))
            conn.commit()
            continue

        if 'text/html' != document.info().get_content_type():
            print("Ignore non text/html page")
            cur.execute('DELETE Pages WHERE url=?', (url,))
            conn.commit()
            continue

        print('('+str(len(html))+')', end=' ')
        soup = BeautifulSoup(html, "html.parser")
        
    except KeyboardInterrupt:
        print('\nProgram interrupted by user...')
        break
    except Exception as e:
        print("Unable to retrieve or parse page:", e)
        cur.execute('UPDATE Pages SET error=-1 WHERE url=?', (url,))
        conn.commit()
        continue

    cur.execute('UPDATE Pages SET html=? WHERE url=?', (memoryview(html), url))
    conn.commit()

    tags = soup('a')
    count = 0
    for tag in tags:
        href = tag.get('href', None)
        if href is None: 
            continue
        
        up = urlparse(href)
        if len(up.scheme) < 1:
            href = urljoin(url, href)
            
        ipos = href.find('#')
        if ipos > 1: 
            href = href[:ipos]
        if href.endswith(('.png', '.jpg', '.gif', '.css', '.js', '.ico')): 
            continue
        if href.endswith('/'): 
            href = href[:-1]
        if len(href) < 1: 
            continue

        if target_domain not in href:
            continue

        cur.execute('INSERT OR IGNORE INTO Pages (url, html, new_rank) VALUES ( ?, NULL, 1.0 )', (href,))
        count += 1
        conn.commit()

        cur.execute('SELECT id FROM Pages WHERE url=? LIMIT 1', (href,))
        row = cur.fetchone()
        if row:
            toid = row[0]
            cur.execute('INSERT OR IGNORE INTO Links (from_id, to_id) VALUES ( ?, ? )', (fromid, toid))
            conn.commit()

    print("Tapılan linklərin sayı:", count)

cur.close()
conn.close()