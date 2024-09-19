from flask import Flask, request, Response, send_file, redirect, url_for
import os
import logging
from twilio.rest import Client
import openai
from app.elevenlabs import generate_voice
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    filename='app.log',  # Log file name
    level=logging.INFO,  # Log level
    format='%(asctime)s %(levelname)s %(message)s'  # Log format
)

app = Flask(__name__)

# Load environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
print(account_sid,auth_token,from_phone_number)
# Initialize the Twilio client
twilio_client = Client(account_sid, auth_token)

# Global variables to store the current customer information and call state
current_customer_name = None
current_customer_phone = None
call_state = {}  # Store state of each call with phone number as key

# Call states
CALL_STATES = {
    'GREETING': 'GREETING',
    'INTRODUCTION': 'INTRODUCTION',
    'SERVICE_INQUIRY': 'SERVICE_INQUIRY',
    'SERVICE_DETAILS': 'SERVICE_DETAILS',
    'FEEDBACK_REQUEST': 'FEEDBACK_REQUEST',
    'THANK_AND_CLOSE': 'THANK_AND_CLOSE'
}

call_prompt = """
You are the outbound voice assistant for Army of Me.

**Goal**: Contact customers to inform them about the accounting services, gather feedback, and answer any questions they might have politely and professionally as a Sales Representative.

**Call Flow:**

1. **Greeting**:
   - Greet the customer using their name.
   - Example: "Hello [Customer Name], this is Ginie from Army of Me. I hope you're doing well today!"

2. **Introduction**:
   - Briefly introduce the services Army of Me offers.
   - Example: "We provide a range of accounting and financial services, including bookkeeping, tax preparation, payroll processing, and more."

3. **Service Inquiry**:
   - Ask if the customer is interested in any specific service or would like an overview.
   - Example: "Is there a particular service you are interested in, or would you like an overview of our offerings?"

4. **Service Details**:
   - If the customer asks about a specific service, identify the service name from their input and provide detailed information using the relevant service details:
     - **Bookkeeping & Accounting Services**: "We offer comprehensive bookkeeping and accounting services starting at $15 per hour, including managing accounts receivable and payable, credit card reconciliation, and year-end closings."
     - **Financial Statement Preparation**: "We prepare accurate financial statements like Income Statements, Balance Sheets, and Cash Flow Statements to help you understand your financial position."
     - **Auditing Services**: "Our internal and external auditing services ensure your financial records' accuracy and compliance with regulations."
     - **Tax Preparation & Planning**: "We provide tax services that meet all regulations while minimizing liabilities and offer strategies for future tax planning."
     - **Payroll Processing**: "Our payroll services include wage calculations, tax withholdings, and timely salary payments while ensuring full compliance."
     - **Management Reporting & Financial Analysis**: "We offer detailed management reporting and financial analysis to provide insights into your business performance."

5. **Service Not Listed**:
   - If the customer asks about a service not covered in the prompt, respond politely:
   - Example: "I'm glad you asked! A Sales Agent will contact you shortly to provide more information. Could you please provide your name, phone number, and the service you’re interested in?"

6. **Interest Confirmation & Logging**:
   - If the customer shows interest in a service, identify the specific service they are interested in and log the details (name, phone number, service name, time) in an Excel sheet. 
   - Example: "Thank you, [Customer Name]. I've noted your interest in our [Service Name]. Our Sales Agent will be in touch with you soon to discuss further details."

7. **Polite Query Handling**:
   - Answer any questions the customer has about the services politely and clearly, maintaining a helpful and professional tone throughout the conversation.

8. **Feedback Request**:
   - Ask for any feedback before ending the call.
   - Example: "Do you have any feedback or additional questions about our services?"

9. **Logging Feedback**:
   - Log any feedback along with the customer's name and the date/time in a feedback log.

10. **Thank and Close**:
    - Thank the customer for their time and end the call politely.
    - Example: "Thank you for your time, [Customer Name]. I appreciate your feedback, and I hope we can assist you in the future. Have a great day!"
"""
# Function to update the service interest Excel sheet
def update_service_interest(client_name, client_phone, service, feedback=None):
    file_name = "service_interest.xlsx"
    data = {
        "Client Name": [client_name],
        "Client Phone": [client_phone],
        "Interested Service": [service],
        "Date": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    }
    if feedback:
        data["Feedback"] = [feedback]

    df = pd.DataFrame(data)

    if os.path.exists(file_name):
        existing_df = pd.read_excel(file_name)
        updated_df = pd.concat([existing_df, df], ignore_index=True)
        updated_df.to_excel(file_name, index=False)
    else:
        df.to_excel(file_name, index=False)

    # Log service interest update
    logging.info(f"Service interest logged: {client_name}, {client_phone}, {service}, {feedback}")

# Function to update the feedback Excel sheet
def update_feedback(client_name, client_phone, feedback):
    file_name = "feedback.xlsx"
    data = {
        "Client Name": [client_name],
        "Client Phone": [client_phone],
        "Feedback": [feedback],
        "Date": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    }
    
    df = pd.DataFrame(data)

    if os.path.exists(file_name):
        existing_df = pd.read_excel(file_name)
        updated_df = pd.concat([existing_df, df], ignore_index=True)
        updated_df.to_excel(file_name, index=False)
    else:
        df.to_excel(file_name, index=False)

    # Log feedback update
    logging.info(f"Feedback logged: {client_name}, {client_phone}, {feedback}")

# Function to update the call state
def update_call_state(phone_number, state):
    call_state[phone_number] = state
    # Log call state update
    logging.info(f"Call state updated: {phone_number} -> {state}")

# Function to get the current call state
def get_call_state(phone_number):
    return call_state.get(phone_number, CALL_STATES['GREETING'])

@app.route("/make-ai-call", methods=['POST'])
def make_ai_call():
    global current_customer_name, current_customer_phone
    client_phone_number = request.form.get('client_phone_number')
    customer_name = request.form.get('customer_name')

    if not client_phone_number or not customer_name:
        logging.error("Client phone number and customer name are required")
        return {"error": "Client phone number and customer name are required"}, 400

    # Store customer name and phone globally
    current_customer_name = customer_name
    current_customer_phone = client_phone_number

    # Set the initial state of the call to GREETING
    update_call_state(client_phone_number, CALL_STATES['GREETING'])

    try:
        call = twilio_client.calls.create(
            from_=from_phone_number,
            to=client_phone_number,
            url=f"http://{request.host}/greet-client"
        )
        logging.info(f"Call initiated: {client_phone_number}, SID: {call.sid}")
        return {"call_sid": call.sid}, 200
    except Exception as e:
        logging.error(f"Error initiating call: {e}")
        return {"error": str(e)}, 500

@app.route("/greet-client", methods=['GET', 'POST'])
def greet_client():
    global current_customer_name, current_customer_phone
    state = get_call_state(current_customer_phone)

    if state == CALL_STATES['GREETING']:
        # Combined greeting and service introduction message
        greeting_text = (
            f"Hello {current_customer_name}, this is Ginie from Army of Me. I hope you're doing well today! "
            "We provide a range of accounting and financial services, including bookkeeping, tax preparation, "
            "payroll processing, and more. Is there a particular service you are interested in, or would you like "
            "an overview of our offerings?"
        )
        audio_url = generate_voice(greeting_text)
        
        # Update the state to service inquiry
        update_call_state(current_customer_phone, CALL_STATES['SERVICE_INQUIRY'])

        response = f"""
        <Response>
            <Play>{audio_url}</Play>
            <Redirect>/gather-input</Redirect>
        </Response>
        """
        logging.info(f"Greeting and service introduction played for: {current_customer_name}")
        return Response(response, mimetype='text/xml')
    else:
        # Handle any unexpected states or reset the call flow if necessary
        logging.warning(f"Unexpected state in greet-client: {state}")
        return redirect(url_for('gather_input'))

@app.route("/gather-input", methods=['GET', 'POST'])
def gather_input():
    global current_customer_phone
    state = get_call_state(current_customer_phone)

    if request.method == 'POST':
        user_input = request.form.get('SpeechResult')

        if user_input and user_input.strip():
            logging.info(f"User input received: {user_input} (State: {state})")

            # Based on current state, decide the next step
            if state == CALL_STATES['INTRODUCTION']:
                update_call_state(current_customer_phone, CALL_STATES['SERVICE_INQUIRY'])
            elif state == CALL_STATES['SERVICE_INQUIRY']:
                update_call_state(current_customer_phone, CALL_STATES['SERVICE_DETAILS'])
            elif state == CALL_STATES['SERVICE_DETAILS']:
                update_call_state(current_customer_phone, CALL_STATES['FEEDBACK_REQUEST'])
            elif state == CALL_STATES['FEEDBACK_REQUEST']:
                update_call_state(current_customer_phone, CALL_STATES['THANK_AND_CLOSE'])

            return redirect(url_for('process_input', user_input=user_input))

    response = """
    <Response>
        <Gather input="speech" action="/gather-input" method="POST" timeout="15" speechTimeout="auto"/>
    </Response>
    """
    return Response(response, mimetype='text/xml')

@app.route("/process_input", methods=['GET', 'POST'])
def process_input():
    global current_customer_name, current_customer_phone
    user_input = request.args.get('user_input', '')
    state = get_call_state(current_customer_phone)

    if not user_input:
        logging.error("User input is required")
        return {"error": "User input is required"}, 400

    try:
        # Use the AI assistant prompt and customer input
        ai_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": call_prompt},
                {"role": "user", "content": f"{current_customer_name}: {user_input}"}
            ]
        ).choices[0].message['content'].strip()

        logging.info(f"AI response generated: {ai_response}")

        # Extract potential service name dynamically from user input
        services = {
            "bookkeeping": "Bookkeeping & Accounting Services",
            "financial statement": "Financial Statement Preparation",
            "auditing": "Auditing Services",
            "tax": "Tax Preparation & Planning",
            "payroll": "Payroll Processing",
            "management reporting": "Management Reporting & Financial Analysis"
        }

        service_name = None
        for key, value in services.items():
            if key in user_input.lower():
                service_name = value
                break

        # State handling logic based on current state and user input
        if state == CALL_STATES['SERVICE_INQUIRY']:
            if service_name:
                # Log service interest dynamically
                update_service_interest(current_customer_name, current_customer_phone, service_name)
                acknowledgment = (
                    f"Thank you, {current_customer_name}. I've noted your interest in our {service_name}. "
                    "A Sales Agent will contact you soon to discuss further details. "
                    "Do you have any feedback or questions about our services?"
                )
                audio_url = generate_voice(acknowledgment)
                update_call_state(current_customer_phone, CALL_STATES['FEEDBACK_REQUEST'])
            else:
                # If not interested or no clear service mentioned
                not_interested_response = (
                    f"Thank you for your time, {current_customer_name}. If you have any future needs, feel free to reach out. "
                    "Have a great day!"
                )
                audio_url = generate_voice(not_interested_response)
                update_call_state(current_customer_phone, CALL_STATES['THANK_AND_CLOSE'])

        elif state == CALL_STATES['FEEDBACK_REQUEST']:
            if "yes" in user_input.lower() or "question" in user_input.lower():
                # If there are queries, handle them (additional logic needed to determine specific questions)
                query_response = (
                    f"Sure, {current_customer_name}. Please feel free to ask any questions you have, and I'll do my best to help."
                )
                audio_url = generate_voice(query_response)

            else:
                # If no more questions or feedback, thank and close
                thank_you_message = f"Thank you for your feedback, {current_customer_name}. We appreciate your time. Have a great day!"
                audio_url = generate_voice(thank_you_message)
                update_call_state(current_customer_phone, CALL_STATES['THANK_AND_CLOSE'])

        else:
            # Default AI response for other states
            audio_url = generate_voice(ai_response)

        # Create and return TwiML response
        response = f"""
        <Response>
            <Play>{audio_url}</Play>
            <Gather input="speech" action="/gather-input" method="POST" timeout="15" speechTimeout="auto"/>
        </Response>
        """
        return Response(response, mimetype='text/xml')

    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return {"error": str(e)}, 500
    
    
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
    logging.info("No input response played.")
    return Response(response, mimetype='text/xml')

@app.route("/output_audio.mp3", methods=['GET'])
def serve_audio():
    try:
        file_path = os.path.join(os.getcwd(), "output_audio.mp3")
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='audio/mpeg')
        else:
            logging.error("File not found: output_audio.mp3")
            return "File not found", 404
    except Exception as e:
        logging.error(f"Error serving audio file: {e}")
        return str(e), 500

if __name__ == "__main__":
    app.run(port=8000)
