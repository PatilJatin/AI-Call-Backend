from flask import Flask, request, Response, send_file, redirect, url_for
import os
from twilio.rest import Client
import openai
from app.elevenlabs import generate_voice

app = Flask(__name__)

# Load environment variables
openai.api_key = ""
account_sid = ""
auth_token = ""  # Replace with your actual auth token
from_phone_number = ""  # Replace with your Twilio phone number

# Initialize the Twilio client with the correct Account SID and Auth Token
twilio_client = Client(account_sid, auth_token)

@app.route("/make-ai-call", methods=['POST'])
def make_ai_call():
    client_phone_number = request.form.get('client_phone_number')

    # Start the call and direct it to the /greet-client route
    call = twilio_client.calls.create(
        from_=from_phone_number,
        to=client_phone_number,
        url=f"http://{request.host}/greet-client"
    )

    return {"call_sid": call.sid}, 200

@app.route("/greet-client", methods=['GET', 'POST'])
def greet_client():
    greeting_text = "Hello, this is your virtual assistant. How can I help you today?"
    audio_url = generate_voice(greeting_text)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Redirect>/gather-input</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/gather-input", methods=['GET', 'POST'])
def gather_input():
    if request.method == 'POST':
        user_input = request.form.get('SpeechResult')
        print(f"User input captured: {user_input}")

        if user_input and user_input.strip():
            if "hang up" in user_input.lower() or "end call" in user_input.lower():
                return redirect(url_for('end_call_response'))
            else:
                return redirect(url_for('process_input', user_input=user_input))
        else:
            return redirect(url_for('are_you_there_response'))
    elif request.method == 'GET':
        response = """
        <Response>
            <Gather input="speech" action="/gather-input" method="POST" timeout="15" speechTimeout="auto"/>
            <Redirect>/no_input_response</Redirect>
        </Response>
        """
        return Response(response, mimetype='text/xml')

@app.route("/are_you_there_response", methods=['GET', 'POST'])
def are_you_there_response():
    ai_response = "Are you there?"
    audio_url = generate_voice(ai_response)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Gather input="speech" action="/gather-input" method="POST" timeout="5" speechTimeout="auto"/>
        <Redirect>/no_input_response</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/no_input_response", methods=['GET','POST'])
def no_input_response():
    ai_response = "Thanks for your time. Goodbye!"
    audio_url = generate_voice(ai_response)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Hangup/>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/end_call_response", methods=['GET'])
def end_call_response():
    ai_response = "Thanks for your time. Goodbye!"
    audio_url = generate_voice(ai_response)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Hangup/>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/process_input", methods=['GET', 'POST'])
def process_input():
    user_input = request.args.get('user_input', '')

    ai_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_input}
        ]
    ).choices[0].message['content'].strip()

    audio_url = generate_voice(ai_response)

    # After AI responds, gather input again with a reasonable timeout to wait for the client’s response
    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Gather input="speech" action="/gather-input" method="POST" timeout="15" speechTimeout="auto"/>
        <Redirect>/are_you_there_response</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/output_audio.mp3", methods=['GET'])
def serve_audio():
    try:
        file_path = os.path.join(os.getcwd(), "output_audio.mp3")
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='audio/mpeg')
        else:
            return "File not found", 404
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run(port=8000)
