import tweepy

# Claves y tokens de acceso
consumer_key = '5WxoPsKfFs3X7HSmGlMokusMt'
consumer_secret = 'nkFUGpTghUJTEChF2iUFrMG616HOn1Bj7JB4a7cL4wUZaGpl8D'
access_token = '1845487569469149184-92UlJEYty4Sgs6jDZeB34JvhnFU1Og'
access_token_secret = 'tUvk4yXa11PAROJ2YgR57Cx2EjMSxFmEO7Ge64e37Om5R'

# Autenticación
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

# API de Twitter
api = tweepy.API(auth)

# Ruta de la imagen y mensaje de estado
imagePath = "img.jpg"
status_text = "Hi! From Python script with image"

try:
    # Paso 1: Subir la imagen usando el endpoint de medios v1.1
    media = api.media_upload(imagePath)
    media_id = media.media_id  # Obtiene el ID de la imagen subida

    # Paso 2: Crear el tweet usando la API v2 con el media_id
    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    # Publica el tweet con el texto y la imagen usando media_id
    response = client.create_tweet(text=status_text, media_ids=[media_id])

    if response:
        print("Tweet publicado con éxito.")
    else:
        print("Error al publicar el tweet.")
except Exception as e:
    print("Error:", e)
