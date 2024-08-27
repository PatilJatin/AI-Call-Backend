from flask import request, Response
from app import app
import openai
from app.elevenlabs import generate_voice
import os

# Load environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')
print(openai.api_key, "open ai key"),
@app.route("/twilio-response", methods=['POST'])
def twilio_response():
    incoming_text = request.values.get('SpeechResult', '')

    if not incoming_text:
        incoming_text = "Hello! How can I assist you today?"

    # Generate AI response using GPT-4
    ai_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": incoming_text}
        ]
    ).choices[0].message['content'].strip()

    # Convert AI response to voice using ElevenLabs
    elevenlabs_voice_url = generate_voice(ai_response)

    # Create Twilio XML response
    response = f"""
    <Response>
        <Say voice="woman">Here is the response from our AI.</Say>
        <Play>{elevenlabs_voice_url}</Play>
    </Response>
    """
    return Response(response, mimetype='text/xml')
