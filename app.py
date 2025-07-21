import gradio as gr
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'utils', '.env'))
import traceback
from agent import run_agent
from utils.tools import check_upcoming_events

# Define the directory where images are stored
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "images")
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def analyze_images_wrapper():
    """Analyzes all images in the designated image directory.

    This function iterates through all image files (PNG, JPG, JPEG) in the
    `IMAGE_DIR`, processes each one using the `run_agent` function, and yields
    progress updates and logs to the Gradio interface.

    Yields:
        A string containing the log of the analysis process.
    """
    image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        return "No images found in the 'images' folder."

    full_log = ""
    for filename in image_files:
        image_path = os.path.join(IMAGE_DIR, filename)
        try:
            yield f"Processing {filename}...\n"
            run_agent(image_path)
            log_message = f"Successfully processed {filename}.\n"
            print(log_message) # For server-side logging
            full_log += log_message
            yield full_log
        except Exception as e:
            error_message = f"Error processing {filename}: {traceback.format_exc()}\n"
            print(error_message)
            full_log += error_message
            yield full_log
    yield full_log + "\nAnalysis complete."

def query_events_wrapper():
    """Queries and returns upcoming events from the database.

    This function acts as a wrapper for `check_upcoming_events` to be used
    within the Gradio interface. It handles any exceptions that occur during
    the query.

    Returns:
        A string containing the list of upcoming events or an error message.
    """
    try:
        return check_upcoming_events()
    except Exception as e:
        return f"Error querying events: {e}"

with gr.Blocks() as demo:
    gr.Markdown("## Image Analysis and Event Query")
    gr.Markdown("Place images in the 'images' folder next to this application, then click 'Analyze Images'.")

    with gr.Row():
        analyze_btn = gr.Button("Analyze Images")
        query_btn = gr.Button("Query Upcoming Events")
    
    output_textbox = gr.Textbox(label="Output", lines=15, interactive=False)

    analyze_btn.click(fn=analyze_images_wrapper, inputs=[], outputs=output_textbox)
    query_btn.click(fn=query_events_wrapper, inputs=[], outputs=output_textbox)

if __name__ == "__main__":
    # It's a good practice to set up your API keys via environment variables
    # For example, create a .env file with your keys
    # from dotenv import load_dotenv
    # load_dotenv()
    demo.launch()