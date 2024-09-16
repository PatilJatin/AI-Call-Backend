import os
import openai
from twilio.rest import Client
from flask import Flask, request, Response, send_file, redirect, url_for, session
from app.elevenlabs import generate_voice

app = Flask(__name__)

app.secret_key = os.urandom(24)


# [Start] Tools Credentials #####################################################################################################################################
openai_api_key = os.getenv('OPENAI_API_KEY')
twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
from_phone_number = os.getenv('FROM_PHONE_NUMBER')
# [End] Tools Credentials #######################################################################################################################################



# Initialize the Twilio client with the correct Account SID and Auth Token ######################################################################################
twilio_client = Client(account_sid, auth_token)


# [Start] Refine the System Message to instruct ChatGPT ########################################################################################################## 
system_message = {
    "role": "system",
    "content": (
        "You are an experienced and persuasive virtual sales assistant. "
        "Your role is to guide clients through their queries, highlight key product features, and address concerns. "
        "Be concise, engaging, and empathetic in your responses."

        "Hello, this is Ginie from Army of Me. I wanted to talk to you about how our accounting services can help your business stay on top of its finances and improve decision-making."
        "As a business owner, you might be interested in knowing how much profit your company has made, what your current stock levels are, your outstanding liabilities, or how much is owed to you by customers. These are important questions that every business needs to answer regularly, whether daily, monthly, or yearly."
        "Our accounting services provide a systematic approach to recording, classifying, and summarizing all your business transactions. This includes generating crucial reports like profit and loss statements, balance sheets, and cash flow statements to give you a clear picture of your financial health."
        "With these insights, you can easily assess your business’s performance, manage your assets and liabilities, and make informed decisions about your company’s future. Our team ensures all your financial transactions are accurately recorded and organized to help you avoid errors and minimize risk."
        "Would you like to learn more about how our accounting services can help streamline your financial processes and improve your business's overall financial health?"
    )
}
# [End] Refine the System Message to instruct ChatGPT ########################################################################################################## 


# [Start] Dynamically Adapt User Input to Create Better Prompts ################################################################################################## 
def enhance_user_input(user_input):
    # Detecting the intent based on keywords (e.g., product query, pricing, support, etc.)
    if "pricing" in user_input.lower():
        return f"The user is asking about the pricing of our product. Provide a clear and concise breakdown of pricing tiers and mention any ongoing discounts."
    elif "features" in user_input.lower():
        return f"The user is asking about the features of our product. Highlight the most important features that differentiate our product from competitors."
    else:
        # For general queries, respond in a conversational and helpful manner
        return f"Engage with the user, answer their question, and guide them toward understanding how the product can meet their needs."
# [End] Dynamically Adapt User Input to Create Better Prompts ################################################################################################## 


# [Start] Predefined Response Templates for Specific Queries #################################################################################################### 
response_templates = {
    "pricing": "Our pricing starts at $99 per month for the basic plan and goes up to $299 for the premium plan, which includes advanced features like {feature}.",
    "features": "Our product offers {key_features} that help you {benefit}."
}

def get_predefined_response(user_input):
    if "pricing" in user_input.lower():
        return response_templates["pricing"].format(feature="priority support")
    elif "features" in user_input.lower():
        return response_templates["features"].format(key_features="real-time analytics, cloud storage, and AI automation", benefit="increase efficiency and reduce costs")
    else:
        return None
# [End] Predefined Response Templates for Specific Queries #################################################################################################### 


# [Start] Main function for AI Sales Calling #####################################################################################################################
@app.route("/make-ai-call", methods=['POST'])
def make_ai_call():
    client_phone_number = request.form.get('client_phone_number')

    # Start the call and direct it to the /greet-client route #####################################################
    call = twilio_client.calls.create(
        from_=from_phone_number,
        to=client_phone_number,
        url=f"http://{request.host}/greet-client"
    )
    return {"call_sid": call.sid}, 200
# [End] Main function for AI Sales Calling #####################################################################################################################


# [Start] Function for greeting the client ########################################################################################################################
@app.route("/greet-client", methods=['GET', 'POST'])
def greet_client():
    greeting_text = "Hello, I am AI Sales Agent from Made In Mars. How can I help you today?"
    audio_url = generate_voice(greeting_text)

    # Create TwiML response to play the audio and redirect for gathering user input ###############################
    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Redirect>/gather-input</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')
# [End] Function for greeting the client ########################################################################################################################


# [Start] Function to gather client's input ########################################################################################################################
@app.route("/gather-input", methods=['GET', 'POST'])
def gather_input():
    if request.method == 'POST':
        user_input = request.form.get('SpeechResult')
        print(f"\n\n === User input captured: {user_input}")

        # Check for specific phrases to end the call ################################################################################
        if user_input and user_input.strip():
            if "hang up" in user_input.lower() or "end call" in user_input.lower():
                return redirect(url_for('end_call_response'))
            else:
                return redirect(url_for('process_input', user_input=user_input))
        else:
            return redirect(url_for('are_you_there_response'))
    elif request.method == 'GET':

        # TwiML to gather speech input with a timeout #################################################################
        response = """
        <Response>
            <Gather input="speech" action="/gather-input" method="POST" timeout="15" speechTimeout="auto"/>
            <Redirect>/no_input_response</Redirect>
        </Response>
        """
        return Response(response, mimetype='text/xml')
# [End] Function to gather client's input ########################################################################################################################


# [Start] Function to process client's input and generate AI response #######################################################################################################
@app.route("/process_input", methods=['GET', 'POST'])
def process_input():
    ######################################################################################################################
    """
    This function takes the client's input and generates an AI response using OpenAI's ChatCompletion.
    The response is converted to audio and played back to the client, after which it gathers more input.
    """
    ######################################################################################################################

    user_input = request.args.get('user_input', '')

    # ai_response = openai.ChatCompletion.create(
    #     model="gpt-4",
    #     messages=[
    #         {"role": "system", "content": "You are a helpful assistant."},
    #         {"role": "user", "content": user_input}
    #     ]
    # ).choices[0].message['content'].strip()



# # 1+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#     # Retrieve conversation history
#     session_conversation = session.get('conversation', [system_message])

#     # Enhance the user input to guide GPT to respond better
#     enhanced_prompt = enhance_user_input(user_input)

#     # Append user input and enhanced prompt to the conversation history
#     session_conversation.append({"role": "user", "content": user_input})
#     session_conversation.append({"role": "system", "content": enhanced_prompt})

#     # Generate AI response
#     ai_response = openai.ChatCompletion.create(
#         model="gpt-4",
#         messages=session_conversation,
#         temperature=0.7,  # Control creativity (lower values make responses more deterministic)
#         max_tokens=150  # Limit response length for quick answers
#     ).choices[0].message['content'].strip()

#     # Append AI's response to conversation history and store it
#     session_conversation.append({"role": "assistant", "content": ai_response})
#     session['conversation'] = session_conversation
# # 1+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



# 2+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Check for predefined response first
    predefined_response = get_predefined_response(user_input)

    if predefined_response:
        # Use the predefined response and generate voice
        audio_url = generate_voice(predefined_response)
    else:
        # If no predefined response exists, proceed with enhancing and generating AI response
        session_conversation = session.get('conversation', [system_message])

        # enhanced_prompt = enhance_user_input(user_input)
        # session_conversation.append({"role": "user", "content": user_input})
        # session_conversation.append({"role": "system", "content": enhanced_prompt})


        # Check if we have a stored prompt from the current session
        if 'stored_prompt' in session:
            stored_prompt = session['stored_prompt']
            enhanced_prompt = f"{stored_prompt} {user_input}"
        else:
            enhanced_prompt = enhance_user_input(user_input)
            session['stored_prompt'] = enhanced_prompt  # Store the enhanced prompt for future use

        session_conversation.append({"role": "user", "content": user_input})
        session_conversation.append({"role": "system", "content": enhanced_prompt})


        ai_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=session_conversation,
            temperature=0.7,
            max_tokens=150
        ).choices[0].message['content'].strip()

        session_conversation.append({"role": "assistant", "content": ai_response})
        session['conversation'] = session_conversation
# 2+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



    audio_url = generate_voice(ai_response)

    # After AI responds, gather input again with a reasonable timeout to wait for the client’s response ######################
    response = f"""
        <Response>
            <Play>{audio_url}</Play>
            <Gather 
                input="speech" 
                action="/gather-input" 
                method="POST" 
                timeout="15" 
                speechTimeout="auto"
            >
                <!-- The AI will actively listen during this pause ############################################################-->
                <Pause length="5"/>  <!-- Pause for 5 seconds  ################################################################-->
            </Gather>
            <Redirect>/are_you_there_response</Redirect>
        </Response>
    """
    return Response(response, mimetype='text/xml')
# [End] Function to process client's input and generate AI response #######################################################################################################


# [Start] Function to check if the client is still there #############################################################################################################
@app.route("/are_you_there_response", methods=['GET', 'POST'])
def are_you_there_response():
    ai_response = "Are you there?"
    audio_url = generate_voice(ai_response)

    # TwiML to play a prompt and gather input again ####################################################################
    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Gather input="speech" action="/gather-input" method="POST" timeout="5" speechTimeout="auto"/>
        <Redirect>/no_input_response</Redirect>
    </Response>
    """
    return Response(response, mimetype='text/xml')
# [End] Function to check if the client is still there #############################################################################################################


# [Start] Function to handle no input case #############################################################################################################################
@app.route("/no_input_response", methods=['GET','POST'])
def no_input_response():
    ai_response = "Thanks for your time. Goodbye!"
    audio_url = generate_voice(ai_response)

    # TwiML to play a goodbye message and hang up the call ##########################################
    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Hangup/>
    </Response>
    """
    return Response(response, mimetype='text/xml')
# [End] Function to handle no input case #############################################################################################################################


# [Start] Function to handle end call response ###########################################################################################################################
@app.route("/end_call_response", methods=['GET'])
def end_call_response():
    ai_response = "Thanks for your time. Goodbye!"
    audio_url = generate_voice(ai_response)

    # Clear the session at the end of the call ############################################################
    session.clear()

    # TwiML to play a goodbye message and hang up the call ################################################
    response = f"""
    <Response>
        <Play>{audio_url}</Play>
        <Hangup/>
    </Response>
    """
    return Response(response, mimetype='text/xml')
# [End] Function to handle end call response ###########################################################################################################################


# [Start] Function to serve audio file #######################################################################################################################################
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
# [End] Function to serve audio file #######################################################################################################################################


if __name__ == "__main__":
    app.run(port=8000)
