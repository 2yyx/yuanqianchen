from gevent.pywsgi import WSGIServer
from flask import Flask, render_template, abort, send_from_directory, redirect, url_for
from werkzeug.utils import safe_join
import os
import glob
import frontmatter
from markdown import Markdown
import yaml
from datetime import datetime
from collections import defaultdict

app = Flask(__name__, static_folder='static', static_url_path='/static')

BASE_DIR = os.path.dirname(__file__)
POSTS_DIR = os.path.join(BASE_DIR, 'content', 'posts')
PAPERS_DIR = os.path.join(BASE_DIR, 'content', 'papers')

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


def load_papers_grouped():
    """Return papers grouped by year as an ordered dict-like mapping year->list of items."""
    meta = {}
    meta_path = os.path.join(PAPERS_DIR, 'papers.yml')
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = yaml.safe_load(f) or {}
        except Exception:
            meta = {}

    items = []
    if os.path.isdir(PAPERS_DIR):
        for p in sorted(os.listdir(PAPERS_DIR)):
            if p.startswith('.'):
                continue
            item = {'filename': p}
            if p in meta:
                item.update(meta[p])
            else:
                item.setdefault('title', os.path.splitext(p)[0])
            # ensure year exists
            if not item.get('year'):
                try:
                    mtime = os.path.getmtime(os.path.join(PAPERS_DIR, p))
                    item['year'] = datetime.fromtimestamp(mtime).year
                except Exception:
                    item['year'] = ''
            items.append(item)

    groups = defaultdict(list)
    for it in items:
        year = str(it.get('year') or 'Unknown')
        groups[year].append(it)

    # sort years descending (try numeric)
    def sort_key(y):
        try:
            return int(y)
        except Exception:
            return -1

    ordered = dict()
    for y in sorted(groups.keys(), key=sort_key, reverse=True):
        ordered[y] = groups[y]
    return ordered

# load at startup; for development you may call load_posts() again to refresh
posts, posts_map = load_posts()

@app.route('/')
def home():
    # Personal homepage: include resume snippet and papers grouped by year
    papers_by_year = load_papers_grouped()
    return render_template('home.html', papers_by_year=papers_by_year)


@app.route('/resume')
def resume():
    return render_template('resume.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/papers')
def papers_index():
    # Use grouped loader and flatten for the papers page
    groups = load_papers_grouped()
    files = []
    for year, items in groups.items():
        for it in items:
            files.append(it)
    return render_template('papers.html', files=files)


@app.route('/papers/download/<path:filename>')
def papers_download(filename):
    # Serve paper files from content/papers
    if not os.path.isdir(PAPERS_DIR):
        abort(404)
    # prevent path traversal
    try:
        safe_path = safe_join(PAPERS_DIR, filename)
    except Exception:
        abort(404)
    if not os.path.exists(safe_path):
        abort(404)
    return send_from_directory(PAPERS_DIR, filename, as_attachment=True)


@app.route('/blog')
def blog_index():
    if RELOAD_ON_REQUEST:
        posts_local, _ = load_posts()
    else:
        posts_local = posts
    return render_template('index.html', posts=posts_local)

@app.route('/blog/post/<slug>')
def post_detail(slug):
    if RELOAD_ON_REQUEST:
        _, posts_map_local = load_posts()
        post = posts_map_local.get(slug)
    else:
        post = posts_map.get(slug)
    if not post:
        abort(404)
    return render_template('post.html', post=post)


# compatibility: redirect old /post/<slug> to new /blog/post/<slug>
@app.route('/post/<slug>')
def post_legacy(slug):
    return redirect(url_for('post_detail', slug=slug))

if __name__ == '__main__':
    keyfile = '/etc/nginx/yuanqianchen.com.key'
    certfile = '/etc/nginx/yuanqianchen.com_bundle.crt'
    if os.path.exists(keyfile) and os.path.exists(certfile):
        http_server = WSGIServer(('', 8081), app, keyfile=keyfile, certfile=certfile)
        http_server.serve_forever()
    else:
        app.run(host='0.0.0.0', port=8081, debug=True)