from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from datetime import datetime
import pickle
import os
import uuid
from bs4 import BeautifulSoup
import base64
import mimetypes
import io

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'


@app.template_filter('to_dict')
def to_dict_filter(obj):
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    return obj


class File:
    def __init__(self, file_data, filename, mimetype):
        self.id = str(uuid.uuid4())
        self.filename = filename
        self.mimetype = mimetype
        self.data = file_data  # Store binary data
        self.upload_date = datetime.now()

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'mimetype': self.mimetype,
            'upload_date': self.upload_date.isoformat()
        }


class Post:
    def __init__(self, title, content, date=None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.content = content
        self.date = date or datetime.now()
        self.read_time = self._calculate_read_time()
        self.excerpt = self._create_excerpt()
        self.files = []  # List to store File objects

    def _calculate_read_time(self):
        # Average reading speed: 200 words per minute
        word_count = len(BeautifulSoup(self.content, 'html.parser').get_text().split())
        minutes = max(1, round(word_count / 200))
        return minutes

    def _create_excerpt(self):
        # Create a clean excerpt from HTML content
        text = BeautifulSoup(self.content, 'html.parser').get_text()
        words = text.split()[:30]  # Take first 30 words
        excerpt = ' '.join(words)
        return excerpt + '...' if len(words) >= 30 else excerpt

    def add_file(self, file_data, filename, mimetype):
        file_obj = File(file_data, filename, mimetype)
        self.files.append(file_obj)
        return file_obj.id

    def get_file(self, file_id):
        return next((f for f in self.files if f.id == file_id), None)

    def remove_file(self, file_id):
        self.files = [f for f in self.files if f.id != file_id]


def save_posts(posts):
    with open('posts.pickle', 'wb') as f:
        pickle.dump(posts, f)


def load_posts():
    if os.path.exists('posts.pickle'):
        with open('posts.pickle', 'rb') as f:
            return pickle.load(f)
    return []


def is_allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    posts = load_posts()
    recent_posts = sorted(posts, key=lambda x: x.date, reverse=True)[:3]
    return render_template('index.html', posts=recent_posts)


@app.route('/blog')
def blog():
    posts = load_posts()
    return render_template('posts-manager.html', posts=posts)


@app.route('/blog/posts')
def blog_list():
    posts = load_posts()
    sorted_posts = sorted(posts, key=lambda x: x.date, reverse=True)
    return render_template('blog-list.html', posts=sorted_posts)


@app.route('/blog/post/<post_id>')
def view_post(post_id):
    posts = load_posts()
    post = next((post for post in posts if post.id == post_id), None)
    if post is None:
        flash('Post not found')
        return redirect(url_for('blog'))
    return render_template('blog-post.html', post=post)


@app.route('/blog/file/<post_id>/<file_id>')
def get_file(post_id, file_id):
    posts = load_posts()
    post = next((post for post in posts if post.id == post_id), None)
    if post:
        file_obj = post.get_file(file_id)
        if file_obj:
            return send_file(
                io.BytesIO(file_obj.data),
                mimetype=file_obj.mimetype,
                as_attachment=True,
                download_name=file_obj.filename
            )
    return 'File not found', 404


@app.route('/blog/new', methods=['POST'])
def new_post():
    title = request.form.get('title')
    content = request.form.get('content')

    if not title or not content:
        flash('Title and content are required')
        return redirect(url_for('blog'))

    posts = load_posts()
    new_post = Post(title=title, content=content)

    # Handle file uploads
    files = request.files.getlist('files')
    for file in files:
        if file and file.filename and is_allowed_file(file.filename):
            file_data = file.read()
            new_post.add_file(file_data, file.filename, file.mimetype)

    posts.append(new_post)
    save_posts(posts)

    flash('Post created successfully')
    return redirect(url_for('blog'))


@app.route('/blog/edit/<post_id>', methods=['POST'])
def edit_post(post_id):
    title = request.form.get('title')
    content = request.form.get('content')

    if not title or not content:
        flash('Title and content are required')
        return redirect(url_for('blog'))

    posts = load_posts()
    post = next((post for post in posts if post.id == post_id), None)

    if post is None:
        flash('Post not found')
        return redirect(url_for('blog'))

    post.title = title
    post.content = content
    post.date = datetime.now()
    post.excerpt = post._create_excerpt()

    # Handle new file uploads
    files = request.files.getlist('files')
    for file in files:
        if file and file.filename and is_allowed_file(file.filename):
            file_data = file.read()
            post.add_file(file_data, file.filename, file.mimetype)

    # Handle file deletions
    files_to_delete = request.form.getlist('delete_files')
    for file_id in files_to_delete:
        post.remove_file(file_id)

    save_posts(posts)

    flash('Post updated successfully')
    return redirect(url_for('blog'))


@app.route('/blog/files/<post_id>')
def get_post_files(post_id):
    posts = load_posts()
    post = next((post for post in posts if post.id == post_id), None)
    if post and post.files:
        return jsonify([file.to_dict() for file in post.files])
    return jsonify([])


@app.route('/blog/delete/<post_id>', methods=['POST'])
def delete_post(post_id):
    posts = load_posts()
    posts = [post for post in posts if post.id != post_id]
    save_posts(posts)

    flash('Post deleted successfully')
    return redirect(url_for('blog'))


if __name__ == '__main__':
    app.run(debug=True)