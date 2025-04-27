import os
import time
from dotenv import load_dotenv
from pymongo import MongoClient
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Load environment variables from .env file
load_dotenv()

# Environment-based configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'jefflix')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'films')
# Base movie directory from environment
BASE_DIRECTORY = os.getenv('MOVIES_PATH')

if not BASE_DIRECTORY:
    raise EnvironmentError('Please set MOVIES_PATH in your .env file')

# Define video extensions and language mapping
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.mpeg', '.mpg'}
LANGUAGE_MAPPING = {
    "spa": "spanish",
    "es": "spanish",
    "spanish": "spanish",
    "eng": "english",
    "en": "english",
    "english": "english",
    "fre": "french",
    "fra": "french",
    "french": "french",
    "ger": "german",
    "de": "german",
    "german": "german",
    "pt": "portuguese",
    "por": "portuguese",
    "portuguese": "portuguese",
    "it": "italian",
    "ita": "italian",
    "italian": "italian",
}

def parse_subtitle_file(filename):
    if not filename.lower().endswith('.srt'):
        return '', False

    base = filename[:-4]
    parts = base.split('.')
    ai_generated = False

    if len(parts) >= 2 and parts[-1].lower() == 'ai':
        ai_generated = True
        language = parts[-2] if len(parts) >= 3 else ''
    elif len(parts) >= 1:
        language = parts[-1]
    else:
        language = ''

    if not language:
        language = 'english'

    return LANGUAGE_MAPPING.get(language.lower(), 'english'), ai_generated


def process_directory(directory_path):
    result = {
        'directory_name': os.path.basename(directory_path),
        'subdirectories': [],
        'video_files': [],
        'subtitle_files': []
    }
    subdirs = set()

    for root, dirs, files in os.walk(directory_path):
        if root != directory_path:
            subdirs.add(os.path.relpath(root, directory_path))
        for file in files:
            full_path = os.path.abspath(os.path.join(root, file))
            ext = os.path.splitext(file)[1].lower()

            if ext == '.srt':
                lang, ai = parse_subtitle_file(file)
                result['subtitle_files'].append({
                    'filename': file,
                    'language': lang,
                    'ai_generated': ai,
                    'full_path': full_path
                })
            elif ext in VIDEO_EXTENSIONS:
                result['video_files'].append({
                    'filename': file,
                    'extension': ext.lstrip('.'),
                    'full_path': full_path
                })

    result['subdirectories'] = list(subdirs)
    return result

class MovieDirectoryEventHandler(FileSystemEventHandler):
    def __init__(self, base_dir, collection):
        self.base_dir = os.path.abspath(base_dir)
        self.collection = collection

    def on_any_event(self, event):
        try:
            rel_path = os.path.relpath(event.src_path, self.base_dir)
            top_dir = rel_path.split(os.sep)[0]
        except ValueError:
            return

        target_path = os.path.join(self.base_dir, top_dir)

        if event.event_type == 'deleted' and event.is_directory:
            self.collection.delete_one({'directory_name': top_dir})
            print(f"Removed document for deleted directory: {top_dir}")
        else:
            if os.path.isdir(target_path):
                data = process_directory(target_path)
                self.collection.update_one(
                    {'directory_name': data['directory_name']},
                    {'$set': data},
                    upsert=True
                )
                print(f"Upserted document for directory: {data['directory_name']}")

if __name__ == '__main__':
    # Validate base directory
    if not os.path.isdir(BASE_DIRECTORY):
        raise NotADirectoryError(f"MOVIES_PATH '{BASE_DIRECTORY}' is not a valid directory.")

    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Initial indexing
    with os.scandir(BASE_DIRECTORY) as entries:
        for entry in entries:
            if entry.is_dir():
                data = process_directory(entry.path)
                collection.update_one(
                    {'directory_name': data['directory_name']},
                    {'$set': data},
                    upsert=True
                )
                print(f"Indexed directory: {data['directory_name']}")

    # Start watcher
    observer = Observer()
    observer.schedule(
        MovieDirectoryEventHandler(BASE_DIRECTORY, collection),
        BASE_DIRECTORY,
        recursive=True
    )
    observer.start()
    print(f"Watching directory for changes: {BASE_DIRECTORY}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

