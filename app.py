import os
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from modules.twitter_handler import TwitterHandler
from modules.instagram_handler import InstagramHandler
from modules.google_services import GoogleServices
from modules.image_processor import ImageProcessor

app = Flask(__name__)

# Load environment variables
TWITTER_SPREADSHEET_ID = os.environ.get('TWITTER_SPREADSHEET_ID')
INSTAGRAM_SPREADSHEET_ID = os.environ.get('INSTAGRAM_SPREADSHEET_ID')
SAMPLE_RANGE_NAME = os.environ.get('SAMPLE_RANGE_NAME', 'X!A2:C')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID')

# Initialize services
google_services = GoogleServices()
twitter_handler = TwitterHandler()
instagram_handler = InstagramHandler()
image_processor = ImageProcessor()

@app.route('/')
def home():
    pending_item = google_services.get_first_pending_item(TWITTER_SPREADSHEET_ID)
    image_data = {}
    if pending_item:
        image_file = google_services.get_image_from_drive(pending_item['column_a'])
        if image_file:
            effects = image_processor.apply_effects(image_file)
            for effect, img in effects.items():
                image_data[effect] = image_processor.image_to_base64(img)

    return render_template('index.html', pending_item=pending_item, image_data=image_data)

@app.route('/tweet', methods=['POST'])
def tweet():
    pending_item = google_services.get_first_pending_item(TWITTER_SPREADSHEET_ID)
    if not pending_item:
        return jsonify({'result': 'No pending items to tweet'}), 400

    image_file = google_services.get_image_from_drive(pending_item['column_a'])
    if not image_file:
        return jsonify({'result': f"Image not found: {pending_item['column_a']}"}), 400

    effect = request.form.get('effect', 'original')
    effects = image_processor.apply_effects(image_file)
    selected_image = effects[effect]

    status_text = pending_item['column_b']
    result = twitter_handler.tweet_with_image(status_text, selected_image)

    if "éxito" in result:
        if google_services.update_sheet_status(TWITTER_SPREADSHEET_ID, pending_item['row_index']):
            result += " La hoja de cálculo ha sido actualizada."
        else:
            result += " Pero hubo un error al actualizar la hoja de cálculo."

    return jsonify({'result': result})

@app.route('/instagram')
def instagram():
    pending_item = google_services.get_first_pending_item(INSTAGRAM_SPREADSHEET_ID)
    image_data = {}
    if pending_item:
        image_file = google_services.get_image_from_drive(pending_item['column_a'])
        if image_file:
            effects = image_processor.apply_effects(image_file)
            for effect, img in effects.items():
                image_data[effect] = image_processor.image_to_base64(img)

    return render_template('instagram.html', pending_item=pending_item, image_data=image_data)

def scheduled_tweet():
    pending_item = google_services.get_first_pending_item(TWITTER_SPREADSHEET_ID)
    if pending_item:
        image_file = google_services.get_image_from_drive(pending_item['column_a'])
        if image_file:
            result = twitter_handler.tweet_with_image(pending_item['column_b'], image_file)
            if "éxito" in result:
                google_services.update_sheet_status(TWITTER_SPREADSHEET_ID, pending_item['row_index'])

# Set up scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_tweet, trigger="interval", hours=24)
scheduler.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)