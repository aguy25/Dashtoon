from flask import Flask, render_template, request, send_file, redirect,url_for
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import re
import os
import logging
app = Flask(__name__)

API_URL = "https://xdwvg9no7pefghrn.us-east-1.aws.endpoints.huggingface.cloud"
HEADERS = {
    "Accept": "image/png",
    "Authorization": "Bearer VknySbLLTUjbxXAXCjyfaFIPwUTCeRXbFSOjwRiCxsxFyhbnGjSFalPKrpvvDAaPVzWEevPljilLVDBiTzfIbWFdxOkYJxnOPoHhkkVGzAknaOulWggusSFewzpqsNWM",
    "Content-Type": "application/json"
}
UNABRIDGED_DIR = 'static/unabridged/'
ABRIDGED_DIR = 'static/'
logging.basicConfig(filename='app.log', level=logging.INFO)
def addLoggingLevel(levelName, levelNum, methodName=None):
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
       raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
       raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
       raise AttributeError('{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)

def query_api(text):
    payload = {"inputs": text}
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.content
    except requests.exceptions.RequestException as e:
        #print(f"Error making API request: {e}")
        logging.error(f"Error making API request: {e}")
        return None  # Return None to indicate failure

def divide_input(input_text, num_lines=10):
    # Split the input at commas and full stops
    sentences = [sentence.strip() for sentence in re.split(r'[,.]', input_text)]
    
    # Filter out empty sentences
    sentences = [sentence for sentence in sentences if sentence]

    # Ensure exactly num_lines sentences
    if len(sentences) < num_lines:
        # If there are not enough sentences, duplicate the last sentence
        sentences += [sentences[-1]] * (num_lines - len(sentences))
    elif len(sentences) > num_lines:
        # If there are too many sentences, truncate the list
        sentences = sentences[:num_lines]
    #print(sentences)
    return sentences

@app.route('/')
def index():
    return render_template('single_input_comic_index.html')

@app.route('/generate_single_input_comic', methods=['POST'])
def generate_single_input_comic():
    input_text = request.form['text']
    
    # Divide the input into 10 sentences
    panel_texts = divide_input(input_text, num_lines=10)
    #print(panel_texts)
    #Generate images for each panel and save the unabridged versions
    for i, text in enumerate(panel_texts):
        print(i)
        image_bytes = query_api(text)
        print("h")
        if image_bytes is not None:
            image = Image.open(io.BytesIO(image_bytes))
        
        # Save the unabridged image
            unabridged_path = os.path.join(UNABRIDGED_DIR, 'panel{}.png'.format(i + 1))
            image.save(unabridged_path)
            abridged_path = os.path.join(ABRIDGED_DIR, 'panel{}.png'.format(i + 1))
            image.save(abridged_path)
        else:
            return render_template('sorry_message.html')
    # Display the generated comic
    return render_template('single_input_comic_result.html', image_paths=[ABRIDGED_DIR + 'panel{}.png'.format(i + 1) for i in range(10)])

@app.route('/download_combined_comic', methods=['POST'])
def download_combined_comic():
    image_paths = request.form['image_paths'].split(',')
    images = [Image.open(path) for path in image_paths]

        # Calculate the maximum width among the images
    max_width = max(img.width for img in images)

    # Calculate the total height of the combined image
    total_height = sum(img.height for img in images)

    # Create a new blank image with the calculated dimensions
    combined_image = Image.new('RGB', (max_width, total_height))

    # Paste each image vertically
    y_offset = 0
    for img in images:
        combined_image.paste(img, (0, y_offset))
        y_offset += img.height

    # Save the combined image temporarily
    combined_image_path = 'static/combined_comic.png'
    combined_image.save(combined_image_path)

    # Provide the combined image for download
    return send_file(combined_image_path, as_attachment=True, download_name='combined_comic.png')

def add_text_to_image(image, text):
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()  # You can customize the font if needed
    draw.text((10, 10), text, (255, 255, 255), font=font)  # Adjust the position as needed

def add_text_to_unabridged_image(panel_number, text):
    unabridged_path = os.path.join(UNABRIDGED_DIR, 'panel{}.png'.format(panel_number))
    abridged_path = os.path.join(ABRIDGED_DIR, 'panel{}.png'.format(panel_number))
    image = Image.open(unabridged_path)
    if text is None or text == "":
        image.save(abridged_path)
        return
    # Increase the height of the image to create whitespace below
    new_width, new_height = image.size
    whitespace_height = 50 # Adjust the height of the whitespace as needed

    # Create a new image with increased height and paste the original image onto it
    new_image = Image.new('RGB', (new_width, new_height + whitespace_height), color=(255, 255, 255))
    new_image.paste(image, (0, 0))  # Paste the original image at the top

    # Add text to the whitespace
    draw = ImageDraw.Draw(new_image)
    font = ImageFont.load_default()  # You can customize the font if needed
    text_position = (10, new_height + 10)  # Adjust the position to control the amount of whitespace
    draw.text(text_position, text, (0, 0, 0), font=font)

    # Save the modified image
    new_image.save(abridged_path)



@app.route('/add_text_to_comic', methods=['POST'])
def add_text_to_comic():
    comic_text = request.form['comic_text']
    panel_number = int(request.form['panel_number'])

    if 1 <= panel_number <= 10:
        add_text_to_unabridged_image(panel_number, comic_text)

    # Display the modified comic
    return render_template('single_input_comic_result.html', image_paths=[ABRIDGED_DIR + 'panel{}.png'.format(i + 1) for i in range(10)])

@app.route('/feedback', methods=['GET'])
def feedback_form():
    return render_template('feedback_form.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback_text = request.form['feedback']
    
    # Here, you can save the feedback to a database or perform any other necessary action.
    # For simplicity, we'll just print the feedback to the console.
    logging.feedback(f"Feedback received: {feedback_text}")
    return  render_template('feedback_message.html') # Redirect to the home page after submitting feedback

if __name__ == '__main__':
    addLoggingLevel('FEEDBACK',logging.INFO+5)
    #logging.feedback("hoho")
    app.run(debug=True)
