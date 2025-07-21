import os
from dotenv import load_dotenv
from agent import run_agent

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

def main():
    """Executes the main image processing workflow.

    This function scans the 'images' directory for image files (PNG, JPG, JPEG),
    and then iterates through each file, calling the `run_agent` function to
    process it. It prints status messages before and after processing each image
    and catches any exceptions that occur during the agent's execution.
    """
    # You can process multiple images by iterating through a directory
    image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    for image_file in os.listdir(image_dir):
        if image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(image_dir, image_file)
  
            


            print(f"--- Processing image: {image_path} ---")
            try:
                run_agent(image_path)
            except Exception as e:
                print(f"An error occurred while processing {image_path}: {e}")
            print(f"--- Finished processing {image_path} ---\n")

if __name__ == "__main__":
    # Example: run agent on a single image
    # image_path = os.path.join(os.path.dirname(__file__), "images", "your_image.jpg")
    # if os.path.exists(image_path):
    #     run_agent(image_path)
    # else:
    #     print(f"Image not found at {image_path}")

    main()
