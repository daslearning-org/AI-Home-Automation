import gradio as gr
import numpy as np
import json
import os

# Import VOSK components
from vosk import KaldiRecognizer, Model

# Import local AI components
from langAi import chat_with_langchain_agent

# Define the audio recognization model. More at: https://alphacephei.com/vosk/models
lang_model = os.environ.get("AUDIO_MODEL", "en-in")

# Load the speach recognization model
try:
    model = Model(lang=lang_model) # You might need to specify model_path= if not in default location
    print("Vosk model loaded successfully.")
except Exception as e:
    print(f"Error loading Vosk model: {e}")
    model = None

# Handles the Text Inputs
def process_text_input(message, history):
    """
    Processes the text input from UI & passes to the backend AI Agent
    """
    updated_history = chat_with_langchain_agent(message=message, history=history)
    return updated_history, updated_history, "" # also clears the text input

# Handles the Audio using VOSK module
def process_audio_input(audio_data_tuple, history):
    # audio_data_tuple will be (sample_rate, numpy_array) from gr.Audio(type="numpy")
    if audio_data_tuple is None or audio_data_tuple[1].size == 0:
        history.append(["Empty Audio!", None])
        history[-1][1] = "I'm sorry, It seems that audio is empty."
        print("No audio data received.")
        return history, history # Return current history for both chatbot and state

    if model is None:
        history.append(["Error: Vosk model not loaded. Cannot transcribe audio.", None])
        history[-1][1] = "I'm sorry, I cannot process audio at the moment. Please use the text input"
        return history, history

    sample_rate, audio_np = audio_data_tuple
    transcribed_text = ""
    fail_flag = False
    user_message = ""
    bot_response = ""

    try:
        # Convert NumPy array to bytes for Vosk
        # Ensure it's 16-bit PCM for Vosk, and mono if stereo
        if audio_np.ndim > 1:
            audio_np = audio_np[:, 0] # Take the first channel for mono
        audio_bytes = audio_np.astype(np.int16).tobytes()

        rec = KaldiRecognizer(model, sample_rate)

        # Process the entire audio waveform
        if rec.AcceptWaveform(audio_bytes):
            result_json = json.loads(rec.Result())
            transcribed_text = result_json.get("text", "")
        else:
            # If AcceptWaveform doesn't immediately give a final result (e.g., if audio is too short)
            # you might get a partial result here, or an empty string.
            # For non-streaming, we expect a final result, but this handles edge cases.
            partial_json = json.loads(rec.PartialResult())
            transcribed_text = partial_json.get("partial", "")
            if not transcribed_text: # Fallback if partial is also empty
                user_message = " (No clear speech detected) "
                bot_response = f"Cannot process the audio as transcription failed"
                fail_flag = True
    except Exception as e:
        print(f"Error during VOSK transcription: {e}")
        user_message = f"Transcription failed: {e}"
        bot_response = f"Cannot process the audio as transcription failed"
        fail_flag = True

    if not transcribed_text.strip():
        user_message = "Audio input (no clear speech detected)."
        bot_response = "I couldn't understand what you said from the audio."
        fail_flag = True
    else: # all went well
        # Simulate bot response based on transcribed text
        user_message = f"{transcribed_text}"
        history = chat_with_langchain_agent(message=user_message, history=history)

    if(fail_flag): # If we get any error during the process
        history.append([user_message, None])
        history[-1][1] = bot_response

    # Return history for chatbot, history for state
    return history, history

# UI using gradio
with gr.Blocks() as demo:
    chatbot = gr.Chatbot()
    state = gr.State([])

    with gr.Row():
        txt = gr.Textbox(show_label=False, lines=1, interactive=True, placeholder="Enter text here...", scale=4)
        send_button = gr.Button("➤", scale=1)
    # Type="numpy" means audio_data will be (sample_rate, numpy_array)
    audio_in = gr.Audio(sources=["microphone"], type="numpy", show_label=False, scale=1)

    # For text input:
    txt.submit(
        process_text_input,
        inputs=[txt, state],
        outputs=[chatbot, state, txt], # chatbot, state, and clear txt
        api_name="text_input"
    )

    send_button.click(
        process_text_input,
        inputs=[txt, state],
        outputs=[chatbot, state, txt], # chatbot, state, and clear txt
    )

    # For audio input:
    # We use .stop_recording to get the full audio chunk after the user stops speaking.
    audio_in.stop_recording(
        process_audio_input,
        inputs=[audio_in, state],
        outputs=[chatbot, state], # chatbot and state
        api_name="audio_input"
    )

demo.launch(server_name="0.0.0.0") # server_name="0.0.0.0" can be used as an argument to make this accessible from other devices
