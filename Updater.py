import requests
import os
import re
import json
from tqdm import tqdm
from dataclasses import dataclass
import glob
import pprint

root = "www.photopea.com/"
website = "https://photopea.com/"
urls = [
    "index.html",
    "style/all.css",
    "code/ext/ext.js",
    "promo/thumb256.png",
    "code/pp/pp.js",
    "code/dbs/DBS.js",
    "rsrc/basic/basic.zip",
    "plugins/gallery.json",
    "code/ext/hb.wasm",
    "code/ext/fribidi.wasm",
    "plugins/tpls/index.html",
    "plugins/tpls/templates.css",
    "plugins/tpls/templates.js",
    "papi/tpls.json",
]

#Update files
def dl_file(path):
    with tqdm(desc=path, unit="B", unit_scale=True) as progress_bar:
        r = requests.get(website + path, stream=True)
        progress_bar.total = int(r.headers.get("Content-Length", 0))

        if r.status_code != 200:
            progress_bar.desc += "ERROR: HTTP Status %d" % r.status_code
            return

        outfn = root + path
        os.makedirs(os.path.dirname(outfn), exist_ok=True)
        with open(outfn, "wb") as outf:
            for chunk in r.iter_content(chunk_size=1024):
                progress_bar.update(len(chunk))
                outf.write(chunk)


for url in urls:
    dl_file(url)

db_data = open(root + "code/dbs/DBS.js").read()
db_vars = re.findall(r"var (\w+)\s*=\s*(\{[\w\W]+?\n\s*\})\s*(?=;|/\*|var)", db_data)
db = {}

for varname, vardata in db_vars:
    print(varname)
    try:
        db[varname] = json.loads(vardata)
    except Exception as e:
        print("Unable to load DBS variable %s: %s" % (varname, e))

#Update fonts
@dataclass
class Font:
    ff: str
    fsf: str
    psn: str
    flg: int
    cat: int
    url: str


def decompress_font_list(flist):
    prev_ff, prev_fsf, prev_flg, prev_cat = "", "", "0", "0"
    for font in flist:
        ff, fsf, psn, flg, cat, url = font.split(",")
        if not ff:
            ff = prev_ff
        if not fsf:
            fsf = prev_fsf
        if not flg:
            flg = prev_flg
        if not cat:
            cat = prev_cat

        if not psn:
            psn = (ff + "-" + fsf).replace(" ", "")
        elif psn == "a":
            psn = ff.replace(" ", "")

        if not url:
            url = "fs/" + psn + ".otf"
        elif url == "a":
            url = "gf/" + psn + ".otf"

        yield Font(ff, fsf, psn, int(flg), int(cat), url)

        prev_ff, prev_fsf, prev_flg, prev_cat = ff, fsf, flg, cat

for font in decompress_font_list(db["FNTS"]["list"]):
    path = "rsrc/fonts/" + font.url
    if not os.path.isfile(root + path):
        dl_file(path)

#Delete any unused fonts
fonts_db=[root+'rsrc/fonts/'+font.url for font in decompress_font_list(db["FNTS"]["list"])]

fonts_local=glob.glob(root + 'rsrc/fonts/'+'/**/*.{otf,ttf,ttc}', recursive=True)

for font_file in list(set(fonts_local)-set(fonts_db)):
    os.remove(font_file)

def find_and_replace(file,find,replace):
    with open(file,'r') as pp:
        file1=pp.read()
    file1=file1.replace(find,replace)
    with open(file,'w') as pp:
        pp.write(file1)

#Allow any port to be used
find_and_replace(root+'/code/pp/pp.js','8887','')

#Don't load Google Analytics
find_and_replace(root+'/index.html','//www.google-analytics.com/analytics.js','')

#Allow the import of pictures of URLs (bypassing mirror.php)
find_and_replace(root+'/code/pp/pp.js','"mirror.php?url="+encodeURIComponent','')