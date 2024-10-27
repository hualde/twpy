import os
import io
import base64
from flask import Flask, render_template, request, jsonify
import tweepy
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.utils import secure_filename
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# Asegúrate de que el directorio de uploads exista
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Twitter API credentials
consumer_key = os.environ['CONSUMER_KEY']
consumer_secret = os.environ['CONSUMER_SECRET']
access_token = os.environ['ACCESS_TOKEN']
access_token_secret = os.environ['ACCESS_TOKEN_SECRET']

# Authenticate with Twitter
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
client = tweepy.Client(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)

# Google API setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly',
          'https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'service_account.json'

creds = None
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# The ID of the spreadsheet and Google Drive folder
SAMPLE_SPREADSHEET_ID = '1K7r5ieDBpvBeqs-qa6hG_pTCiqUDbwIW6e9rU8zwa30'
SAMPLE_RANGE_NAME = 'X!A2:C'
DRIVE_FOLDER_ID = '1eBTlJykWWl8oQ8mM5mw0IzKIyjtBJm8H'

def get_first_pending_item():
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        values = result.get('values', [])

        if not values:
            print('No data found.')
            return None
        else:
            for row in values:
                if len(row) >= 3 and row[2].lower() == 'pendiente':
                    return {
                        'column_a': row[0],
                        'column_b': row[1]
                    }

        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_image_from_drive(file_name):
    try:
        service = build('drive', 'v3', credentials=creds)

        # Search for the file in the specified folder
        query = f"name = '{file_name}' and '{DRIVE_FOLDER_ID}' in parents"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            print(f'No file found with name: {file_name}')
            return None

        file_id = items[0]['id']

        # Download the file
        request = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        file.seek(0)
        return file

    except Exception as e:
        print(f"An error occurred while fetching the image: {e}")
        return None

def apply_effects(image):
    original = Image.open(image)
    greyscale = ImageOps.grayscale(original)
    blur = original.filter(ImageFilter.GaussianBlur(radius=5))
    contrast = ImageEnhance.Contrast(original).enhance(1.5)

    return {
        'original': original,
        'greyscale': greyscale,
        'blur': blur,
        'contrast': contrast
    }

def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def tweet_with_image(status_text, image_file):
    try:
        # Upload image
        media = api.media_upload(filename="image.jpg", file=image_file)
        media_id = media.media_id

        # Create tweet
        response = client.create_tweet(text=status_text, media_ids=[media_id])

        if response:
            return "Tweet published successfully."
        else:
            return "Error publishing tweet."
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/')
def home():
    pending_item = get_first_pending_item()
    image_data = {}
    if pending_item:
        image_file = get_image_from_drive(pending_item['column_a'])
        if image_file:
            effects = apply_effects(image_file)
            for effect, img in effects.items():
                image_data[effect] = image_to_base64(img)
    return render_template('index.html', pending_item=pending_item, image_data=image_data)

@app.route('/tweet', methods=['POST'])
def tweet():
    pending_item = get_first_pending_item()
    if not pending_item:
        return jsonify({'result': 'No pending items to tweet'}), 400

    image_file = get_image_from_drive(pending_item['column_a'])
    if not image_file:
        return jsonify({'result': f"Image not found: {pending_item['column_a']}"}), 400

    effect = request.form.get('effect', 'original')
    effects = apply_effects(image_file)
    selected_image = effects[effect]

    buffered = io.BytesIO()
    selected_image.save(buffered, format="JPEG")
    buffered.seek(0)

    status_text = pending_item['column_b']
    result = tweet_with_image(status_text, buffered)
    return jsonify({'result': result})

def scheduled_tweet():
    pending_item = get_first_pending_item()
    if pending_item:
        image_file = get_image_from_drive(pending_item['column_a'])
        if image_file:
            tweet_with_image(pending_item['column_b'], image_file)

# Set up scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_tweet, trigger="interval", hours=24)
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True)