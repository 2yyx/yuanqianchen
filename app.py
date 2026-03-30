from gevent.pywsgi import WSGIServer
from flask import Flask, render_template, abort
import os
import glob
import frontmatter
from markdown import Markdown

app = Flask(__name__, static_folder='static', static_url_path='/static')

BASE_DIR = os.path.dirname(__file__)
POSTS_DIR = os.path.join(BASE_DIR, 'content', 'posts')

# When True, reload Markdown files on each request (useful for development).
RELOAD_ON_REQUEST = True

def load_posts():
    posts = []
    posts_map = {}
    if not os.path.isdir(POSTS_DIR):
        return posts, posts_map
    for path in glob.glob(os.path.join(POSTS_DIR, '*.md')):
        try:
            fm = frontmatter.load(path)
        except Exception:
            continue
        meta = fm.metadata
        slug = os.path.splitext(os.path.basename(path))[0]
        title = meta.get('title', slug)
        date = meta.get('date', '')
        summary = meta.get('summary', '')
        def render_md(text):
            md = Markdown(extensions=['fenced_code', 'codehilite', 'tables', 'attr_list'],
                          extension_configs={
                              'codehilite': {'guess_lang': False, 'css_class': 'codehilite'},
                          })
            html = md.convert(text)
            md.reset()
            return html

        html = render_md(fm.content)
        post = {
            'title': title,
            'slug': slug,
            'date': date,
            'summary': summary,
            'content': html,
            'raw_content': fm.content
        }
        posts.append(post)
        posts_map[slug] = post
    # Sort by date descending if possible (assumes YYYY-MM-DD)
    try:
        posts.sort(key=lambda p: p.get('date',''), reverse=True)
    except Exception:
        pass
    return posts, posts_map

# load at startup; for development you may call load_posts() again to refresh
posts, posts_map = load_posts()

@app.route('/')
def index():
    if RELOAD_ON_REQUEST:
        posts, _ = load_posts()
    else:
        posts_local = posts
        posts = posts_local
    return render_template('index.html', posts=posts)

@app.route('/post/<slug>')
def post_detail(slug):
    if RELOAD_ON_REQUEST:
        _, posts_map_local = load_posts()
        post = posts_map_local.get(slug)
    else:
        post = posts_map.get(slug)
    if not post:
        abort(404)
    return render_template('post.html', post=post)

if __name__ == '__main__':
    keyfile = '/etc/nginx/yuanqianchen.com.key'
    certfile = '/etc/nginx/yuanqianchen.com_bundle.crt'
    if os.path.exists(keyfile) and os.path.exists(certfile):
        http_server = WSGIServer(('', 8081), app, keyfile=keyfile, certfile=certfile)
        http_server.serve_forever()
    else:
        app.run(host='0.0.0.0', port=8081, debug=True)