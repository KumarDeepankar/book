from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import pickle
import os
import uuid
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

class Post:
    def __init__(self, title, content, date=None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.content = content
        self.date = date or datetime.now()
        self.read_time = self._calculate_read_time()
        self.excerpt = self._create_excerpt()

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

def save_posts(posts):
    with open('posts.pickle', 'wb') as f:
        pickle.dump(posts, f)

def load_posts():
    if os.path.exists('posts.pickle'):
        with open('posts.pickle', 'rb') as f:
            return pickle.load(f)
    return []

@app.route('/')
def home():
    posts = load_posts()
    # Sort posts by date, newest first, and take the latest 3
    recent_posts = sorted(posts, key=lambda x: x.date, reverse=True)[:3]
    return render_template('index.html', posts=recent_posts)

@app.route('/blog')
def blog():
    posts = load_posts()
    return render_template('posts-manager.html', posts=posts)

@app.route('/blog/posts')
def blog_list():
    posts = load_posts()
    # Sort posts by date, newest first
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

@app.route('/blog/new', methods=['POST'])
def new_post():
    title = request.form.get('title')
    content = request.form.get('content')

    if not title or not content:
        flash('Title and content are required')
        return redirect(url_for('blog'))

    posts = load_posts()
    new_post = Post(title=title, content=content)
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
    post.excerpt = post._create_excerpt()  # Update excerpt when content changes
    save_posts(posts)

    flash('Post updated successfully')
    return redirect(url_for('blog'))

@app.route('/blog/delete/<post_id>', methods=['POST'])
def delete_post(post_id):
    posts = load_posts()
    posts = [post for post in posts if post.id != post_id]
    save_posts(posts)

    flash('Post deleted successfully')
    return redirect(url_for('blog'))

if __name__ == '__main__':
    app.run(debug=True)