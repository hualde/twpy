import os
from flask import Flask, render_template, request, jsonify
import tweepy
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.utils import secure_filename
from google.oauth2 import service_account
from googleapiclient.discovery import build

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

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = 'service_account.json'

creds = None
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1K7r5ieDBpvBeqs-qa6hG_pTCiqUDbwIW6e9rU8zwa30'
SAMPLE_RANGE_NAME = 'X!A2:C'

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

def tweet_with_image(status_text, image_file):
    try:
        # Upload image
        media = api.media_upload(filename=image_file)
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
    return render_template('index.html', pending_item=pending_item)

@app.route('/tweet', methods=['POST'])
def tweet():
    status_text = request.form['status']
    if 'image' not in request.files:
        return jsonify({'result': 'No file part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'result': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        result = tweet_with_image(status_text, filepath)
        os.remove(filepath)  # Eliminar el archivo después de usarlo
        return jsonify({'result': result})

def scheduled_tweet():
    tweet_with_image("Scheduled tweet!", "path_to_image.jpg")

# Set up scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_tweet, trigger="interval", hours=24)
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True)