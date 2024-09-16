import requests
import os

def generate_voice(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB"
    headers = {
        'xi-api-key': 'sk_313167b34a9da0fffb3417bbd325e36dc5ed0edcebd1b436',
        'Content-Type': 'application/json',
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.1,
            "similarity_boost": 0.3,
            "style": 0.2,
            "optimize_streaming_latency": "0",
            "output_format": "mp3_22050_32"
        }
    }

    response = requests.post(url, headers=headers, json=data)

    # Log response for debugging
    print("Response Status Code:", response.status_code)
    print("Response Headers:", response.headers)

    # Check if response is JSON or binary data
    if response.headers['Content-Type'] == 'application/json':
        try:
            json_response = response.json()
            return json_response.get('url')
        except ValueError:
            raise Exception("Response is not a valid JSON")
    elif response.headers['Content-Type'].startswith('audio/'):
        # If the content is audio, save it to a file and return the file path
        file_path = 'output_audio.mp3'
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_path
    else:
        raise Exception(f"Unexpected content type: {response.headers['Content-Type']}, Response: {response.text}")

# Example usage
if __name__ == "__main__":
    text_to_speak = "Hello, how can I help you today?"
    try:
        audio_url_or_file = generate_voice(text_to_speak)
        print("Generated Audio File:", audio_url_or_file)
    except Exception as e:
        print("An error occurred:", str(e))
