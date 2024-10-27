import os
import tweepy
import io
from PIL import Image

class TwitterHandler:
    def __init__(self):
        self.consumer_key = os.environ.get('CONSUMER_KEY')
        self.consumer_secret = os.environ.get('CONSUMER_SECRET')
        self.access_token = os.environ.get('ACCESS_TOKEN')
        self.access_token_secret = os.environ.get('ACCESS_TOKEN_SECRET')

        self.auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        self.auth.set_access_token(self.access_token, self.access_token_secret)
        self.api = tweepy.API(self.auth)

    def tweet_with_image(self, status_text, image):
        try:
            # Ensure image is a PIL Image object
            if not isinstance(image, Image.Image):
                image = Image.open(image)

            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)

            # Upload the image
            media = self.api.media_upload(filename="image.jpg", file=img_byte_arr)
            media_id = media.media_id

            # Create tweet with uploaded image
            client = tweepy.Client(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret
            )

            response = client.create_tweet(text=status_text, media_ids=[media_id])

            if response:
                return "Tweet publicado con éxito."
            else:
                return "Error al publicar el tweet."
        except Exception as e:
            return f"Error: {str(e)}"