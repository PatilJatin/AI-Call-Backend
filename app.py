from flask import Flask, request, Response, send_file, redirect, url_for
import os
from twilio.rest import Client
import openai
from app.elevenlabs import generate_voice
import time

app = Flask(__name__)

# Load environment variables
openai.api_key = ""
account_sid = ""
auth_token = ""  # Replace with your actual auth token
from_phone_number = ""  # Replace with your Twilio phone number

# Initialize the Twilio client with the correct Account SID and Auth Token
twilio_client = Client(account_sid, auth_token)

# Define the reference text for the AI to use
reference_text = """
You are an outbound voice assistant for Made In Mars. Your goal is to contact customers to inform them about the launch of a new product, gather feedback, and answer any questions they might have.

Call Flow:
- Introduce yourself and state that you are calling from Made in Mars Inc.
- Confirm you are speaking with the customer and inform them about the launch of a new skateboard model.
- Ask if they have any feedback or questions about the new product.
- Offer detailed information if they have any questions or concerns.

Background:
You are an AI assistant created by Army of Me to inform customers about our latest product launches and gather valuable feedback (AI-enabled HRMS, Accounting, and Inventory). We provide AI consulting and AI implementation services.

Your tasks include:
- Answering questions about the business and booking appointments.
- Gathering necessary information from callers in a friendly and efficient manner.

Steps for Appointment Booking:
- Ask for their full name.
- Request their preferred date and time for the appointment.
- Confirm all details with the caller, including the date and time of the appointment.
- Thank them for their time and provide contact info if they need to get in touch.

Closing:
- Thank the customer for their time and offer further assistance if needed.
"""

@app.route("/make-ai-call", methods=['POST'])
def make_ai_call():
    client_phone_number = request.form.get('client_phone_number')
    customer_name = request.form.get('customer_name')

    if not customer_name:
        customer_name = "Customer"

    # Start the call and direct it to the /greet-client route, passing the customer_name in the URL
    call = twilio_client.calls.create(
        from_=from_phone_number,
        to=client_phone_number,
        url=f"http://{request.host}/greet-client?customer_name={customer_name}"
    )

    return {"call_sid": call.sid}, 200

@app.route("/greet-client", methods=['GET', 'POST'])
def greet_client():
    # Retrieve the customer_name from the URL parameters
    customer_name = request.args.get('customer_name', 'Customer')
    print(f"Greeting {customer_name}...")  # Debugging line

    greeting_text = f"Hello {customer_name}, my name is Ginie, and I’m calling from Made in Mars. How are you today? I’m excited to share some of our fantastic products with you, including high-quality skateboards, innovative pet products, and strollers for kids. Do you have a moment to talk?"
    audio_url = generate_voice(greeting_text)

    # Pass the customer_name in the URL for the next route
    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Redirect>/process-interest?customer_name={customer_name}</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/process-interest", methods=['POST', 'GET'])
def process_interest():
    customer_name = request.args.get('customer_name', 'Customer')

    if request.method == 'POST':
        user_input = request.form.get('SpeechResult')
        print(f"User input captured: {user_input}")  # Debugging line

        if user_input and user_input.strip():
            if "yes" in user_input.lower():
                return redirect(url_for('provide_details', customer_name=customer_name))
            elif "no" in user_input.lower():
                return redirect(url_for('thank_you', customer_name=customer_name))
            else:
                return redirect(url_for('ask_for_feedback', customer_name=customer_name))
        else:
            return redirect(url_for('are_you_there_response', customer_name=customer_name))

    # If GET request, handle the initial response
    response_text = f"{reference_text}\n\nAre you interested in learning more about our new skateboard model?"
    audio_url = generate_voice(response_text)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Gather input="speech" action="/process-interest?customer_name={customer_name}" method="POST" timeout="15" speechTimeout="auto"/>
        <Redirect>/no_input_response?customer_name={customer_name}</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/provide_details", methods=['GET', 'POST'])
def provide_details():
    customer_name = request.args.get('customer_name', 'Customer')
    response_text = f"Great! Our new skateboard model is lightweight, durable, and perfect for all skill levels. Would you like to know more about it or have any other questions?"
    audio_url = generate_voice(response_text)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Gather input="speech" action="/ask_for_feedback?customer_name={customer_name}" method="POST" timeout="15" speechTimeout="auto"/>
        <Redirect>/no_input_response?customer_name={customer_name}</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/ask_for_feedback", methods=['GET', 'POST'])
def ask_for_feedback():
    customer_name = request.args.get('customer_name', 'Customer')
    response_text = f"Do you have any feedback or questions about our new products?"
    audio_url = generate_voice(response_text)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Gather input="speech" action="/thank_you?customer_name={customer_name}" method="POST" timeout="15" speechTimeout="auto"/>
        <Redirect>/no_input_response?customer_name={customer_name}</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/thank_you", methods=['GET', 'POST'])
def thank_you():
    customer_name = request.args.get('customer_name', 'Customer')
    response_text = f"Thank you for your time, {customer_name}. I hope I’ve given you a good overview of our skateboards, pet products, and kids’ strollers. If you have any questions or need more information, feel free to contact us. Have a great day!"
    audio_url = generate_voice(response_text)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Hangup/>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/are_you_there_response", methods=['GET', 'POST'])
def are_you_there_response():
    customer_name = request.args.get('customer_name', 'Customer')
    ai_response = "Are you there?"
    audio_url = generate_voice(ai_response)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Gather input="speech" action="/ask_for_feedback?customer_name={customer_name}" method="POST" timeout="5" speechTimeout="auto"/>
        <Redirect>/no_input_response?customer_name={customer_name}</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/no_input_response", methods=['GET', 'POST'])
def no_input_response():
    customer_name = request.args.get('customer_name', 'Customer')
    ai_response = "Thanks for your time. Goodbye!"
    audio_url = generate_voice(ai_response)

    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Hangup/>
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
