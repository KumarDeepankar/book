from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
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


class Meeting:
    def __init__(self, name, email, date, time):
        self.id = str(uuid.uuid4())
        self.name = name
        self.email = email
        self.date = date
        self.time = time
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'date': self.date,
            'time': self.time,
            'created_at': self.created_at.isoformat()
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
        self.chapters = self._extract_chapters()

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

    def _extract_chapters(self):
        """Extract chapters from content based on h2 headers."""
        soup = BeautifulSoup(self.content, 'html.parser')
        chapters = []

        # Find all h2 elements
        headers = soup.find_all('h2')

        for i, header in enumerate(headers):
            # Generate an ID for the header if it doesn't have one
            header_id = f'chapter-{i + 1}'

            # Update the actual content with the ID
            header['id'] = header_id

            chapters.append({
                'id': header_id,
                'title': header.get_text(),
                'number': i + 1
            })

        # Update the content with the modified HTML
        self.content = str(soup)

        return chapters

    def add_file(self, file_data, filename, mimetype):
        file_obj = File(file_data, filename, mimetype)
        self.files.append(file_obj)
        return file_obj.id

    def get_file(self, file_id):
        return next((f for f in self.files if f.id == file_id), None)

    def remove_file(self, file_id):
        self.files = [f for f in self.files if f.id != file_id]

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'date': self.date.isoformat(),
            'read_time': self.read_time,
            'excerpt': self.excerpt,
            'chapters': self.chapters
        }

# class Post:
#     def __init__(self, title, content, date=None):
#         self.id = str(uuid.uuid4())
#         self.title = title
#         self.content = content
#         self.date = date or datetime.now()
#         self.read_time = self._calculate_read_time()
#         self.excerpt = self._create_excerpt()
#         self.files = []  # List to store File objects
#
#     def _calculate_read_time(self):
#         # Average reading speed: 200 words per minute
#         word_count = len(BeautifulSoup(self.content, 'html.parser').get_text().split())
#         minutes = max(1, round(word_count / 200))
#         return minutes
#
#     def _create_excerpt(self):
#         # Create a clean excerpt from HTML content
#         text = BeautifulSoup(self.content, 'html.parser').get_text()
#         words = text.split()[:30]  # Take first 30 words
#         excerpt = ' '.join(words)
#         return excerpt + '...' if len(words) >= 30 else excerpt
#
#     def add_file(self, file_data, filename, mimetype):
#         file_obj = File(file_data, filename, mimetype)
#         self.files.append(file_obj)
#         return file_obj.id
#
#     def get_file(self, file_id):
#         return next((f for f in self.files if f.id == file_id), None)
#
#     def remove_file(self, file_id):
#         self.files = [f for f in self.files if f.id != file_id]


def save_posts(posts):
    with open('posts.pickle', 'wb') as f:
        pickle.dump(posts, f)


def load_posts():
    if os.path.exists('posts.pickle'):
        with open('posts.pickle', 'rb') as f:
            return pickle.load(f)
    return []


def save_meetings(meetings):
    with open('meetings.pickle', 'wb') as f:
        pickle.dump(meetings, f)


def load_meetings():
    if os.path.exists('meetings.pickle'):
        with open('meetings.pickle', 'rb') as f:
            return pickle.load(f)
    return []


def check_overlap(meetings, new_date, new_time):
    new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")

    # Consider a meeting to be 1 hour long
    new_end = new_datetime + timedelta(hours=1)

    for meeting in meetings:
        existing_datetime = datetime.strptime(f"{meeting.date} {meeting.time}", "%Y-%m-%d %H:%M")
        existing_end = existing_datetime + timedelta(hours=1)

        if (new_datetime < existing_end and new_end > existing_datetime):
            return True
    return False


def is_allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    posts = load_posts()
    recent_posts = sorted(posts, key=lambda x: x.date, reverse=True)[:3]
    return render_template('index.html', posts=recent_posts, datetime=datetime)


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


@app.route('/meetings')
def view_meetings():
    meetings = load_meetings()
    sorted_meetings = sorted(meetings, key=lambda x: f"{x.date} {x.time}")
    return render_template('meetings.html', meetings=sorted_meetings)


@app.route('/schedule-meeting', methods=['POST'])
def schedule_meeting():
    data = request.form
    name = data.get('name')
    email = data.get('email')
    date = data.get('date')
    time = data.get('time')

    if not all([name, email, date, time]):
        return jsonify({'error': 'All fields are required'}), 400

    # Validate date and time
    try:
        meeting_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        if meeting_datetime < datetime.now():
            return jsonify({'error': 'Cannot schedule meetings in the past'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid date or time format'}), 400

    meetings = load_meetings()

    # Check for overlaps
    if check_overlap(meetings, date, time):
        return jsonify({'error': 'This time slot is already booked'}), 400

    new_meeting = Meeting(name, email, date, time)
    meetings.append(new_meeting)
    save_meetings(meetings)

    return jsonify({'message': 'Meeting scheduled successfully'})


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


@app.route('/blog/delete/<post_id>', methods=['POST'])
def delete_post(post_id):
    posts = load_posts()
    posts = [post for post in posts if post.id != post_id]
    save_posts(posts)

    flash('Post deleted successfully')
    return redirect(url_for('blog'))


@app.route('/meeting/delete/<meeting_id>', methods=['POST'])
def delete_meeting(meeting_id):
    meetings = load_meetings()
    meetings = [meeting for meeting in meetings if meeting.id != meeting_id]
    save_meetings(meetings)

    flash('Meeting deleted successfully')
    return redirect(url_for('view_meetings'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)