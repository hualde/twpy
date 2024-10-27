import os
import logging
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from modules.twitter_handler import TwitterHandler
from modules.instagram_handler import InstagramHandler
from modules.google_services import GoogleServices
from modules.image_processor import ImageProcessor

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
TWITTER_SPREADSHEET_ID = os.environ.get('TWITTER_SPREADSHEET_ID')
INSTAGRAM_SPREADSHEET_ID = os.environ.get('INSTAGRAM_SPREADSHEET_ID')
SAMPLE_RANGE_NAME = os.environ.get('SAMPLE_RANGE_NAME', 'X!A2:C')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID')

# Log environment variables (be careful not to log sensitive information)
logging.info(f"TWITTER_SPREADSHEET_ID: {TWITTER_SPREADSHEET_ID}")
logging.info(f"INSTAGRAM_SPREADSHEET_ID: {INSTAGRAM_SPREADSHEET_ID}")
logging.info(f"SAMPLE_RANGE_NAME: {SAMPLE_RANGE_NAME}")
logging.info(f"DRIVE_FOLDER_ID: {DRIVE_FOLDER_ID}")

# Check if required environment variables are set
required_vars = ['TWITTER_SPREADSHEET_ID', 'INSTAGRAM_SPREADSHEET_ID', 'DRIVE_FOLDER_ID', 'GOOGLE_APPLICATION_CREDENTIALS']
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize services
google_services = GoogleServices()
twitter_handler = TwitterHandler()
instagram_handler = InstagramHandler()
image_processor = ImageProcessor()

@app.route('/')
def home():
    logging.info("Accessing home route")
    if not TWITTER_SPREADSHEET_ID:
        logging.error("TWITTER_SPREADSHEET_ID is not set")
        return render_template('error.html', error="Twitter Spreadsheet ID is not configured"), 500

    pending_item = google_services.get_first_pending_item(TWITTER_SPREADSHEET_ID)
    logging.info(f"Pending item for Twitter: {pending_item}")
    image_data = {}
    if pending_item:
        image_file = google_services.get_image_from_drive(pending_item['column_a'])
        if image_file:
            effects = image_processor.apply_effects(image_file)
            for effect, img in effects.items():
                image_data[effect] = image_processor.image_to_base64(img)
        else:
            logging.warning(f"Image file not found: {pending_item['column_a']}")
    else:
        logging.warning("No pending items found for Twitter")

    return render_template('index.html', pending_item=pending_item, image_data=image_data)

@app.route('/tweet', methods=['POST'])
def tweet():
    logging.info("Accessing tweet route")
    if not TWITTER_SPREADSHEET_ID:
        logging.error("TWITTER_SPREADSHEET_ID is not set")
        return jsonify({'result': 'Twitter Spreadsheet ID is not configured'}), 500

    pending_item = google_services.get_first_pending_item(TWITTER_SPREADSHEET_ID)
    if not pending_item:
        logging.warning("No pending items to tweet")
        return jsonify({'result': 'No pending items to tweet'}), 400

    image_file = google_services.get_image_from_drive(pending_item['column_a'])
    if not image_file:
        logging.warning(f"Image not found: {pending_item['column_a']}")
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

    logging.info(f"Tweet result: {result}")
    return jsonify({'result': result})

@app.route('/instagram')
def instagram():
    logging.info("Accessing Instagram route")
    if not INSTAGRAM_SPREADSHEET_ID:
        logging.error("INSTAGRAM_SPREADSHEET_ID is not set")
        return render_template('error.html', error="Instagram Spreadsheet ID is not configured"), 500

    pending_item = google_services.get_first_pending_item(INSTAGRAM_SPREADSHEET_ID)
    logging.info(f"Pending item for Instagram: {pending_item}")
    image_data = {}
    if pending_item:
        image_file = google_services.get_image_from_drive(pending_item['column_a'])
        if image_file:
            effects = image_processor.apply_effects(image_file)
            for effect, img in effects.items():
                image_data[effect] = image_processor.image_to_base64(img)
        else:
            logging.warning(f"Image file not found: {pending_item['column_a']}")
    else:
        logging.warning("No pending items found for Instagram")

    return render_template('instagram.html', pending_item=pending_item, image_data=image_data)

def scheduled_tweet():
    logging.info("Running scheduled tweet")
    if not TWITTER_SPREADSHEET_ID:
        logging.error("TWITTER_SPREADSHEET_ID is not set for scheduled tweet")
        return

    pending_item = google_services.get_first_pending_item(TWITTER_SPREADSHEET_ID)
    if pending_item:
        image_file = google_services.get_image_from_drive(pending_item['column_a'])
        if image_file:
            result = twitter_handler.tweet_with_image(pending_item['column_b'], image_file)
            if "éxito" in result:
                google_services.update_sheet_status(TWITTER_SPREADSHEET_ID, pending_item['row_index'])
        else:
            logging.warning(f"Image file not found for scheduled tweet: {pending_item['column_a']}")
    else:
        logging.warning("No pending items found for scheduled tweet")

# Set up scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_tweet, trigger="interval", hours=24)
scheduler.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)