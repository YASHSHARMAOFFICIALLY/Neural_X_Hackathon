"""
SNOTRA-AI
A comprehensive educational platform with AI-powered features
"""
from dotenv import load_dotenv
load_dotenv()


from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
import os
import json
from google import genai
from google.genai import types

from datetime import datetime
import PyPDF2
import docx
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'docx', 'md'}

@app.route('/test-api')
def test():
    return {"status": "Backend is reachable!"}

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
import os
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize Anthropic client (API key should be set in environment)

GOOGLE_API_KEYS = [
    os.environ.get("GOOGLE_API_KEY1"),
    os.environ.get("GOOGLE_API_KEY2"),
    os.environ.get("GOOGLE_API_KEY3")
]


# Use 'gemini-1.5-flash' for speed and high free-tier limits


# YouTube API configuration
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def extract_text_from_file(filepath):
    """Extract text content from uploaded files"""
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    
    try:
        if ext == '.txt' or ext == '.md':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif ext == '.pdf':
            text = []
            with open(filepath, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return '\n'.join(text)
        
        elif ext == '.docx':
            doc = docx.Document(filepath)
            text = [paragraph.text for paragraph in doc.paragraphs]
            return '\n'.join(text)
        
        else:
            return None
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None



import random # Add this to your imports at the top

# ... other imports ...

# 1. Collect all keys into a list

# Filter out None values in case one key is missing in .env
GOOGLE_API_KEYS = [k for k in GOOGLE_API_KEYS if k]

def call_gemini(system_prompt, user_message, max_tokens=2000):
    try:
        if not GOOGLE_API_KEYS:
            print("ERROR: No API keys found.")
            return None
        
        # 1. Randomly pick a key
        selected_key = random.choice(GOOGLE_API_KEYS)
        
        # 2. Initialize the Client
        client = genai.Client(api_key=selected_key)
        
        # 3. Request generation (Model name goes here now)
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Use 1.5-flash for stable hackathon performance
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

def search_youtube_videos(query, max_results=5):
    """Search for educational videos on YouTube"""
    if not YOUTUBE_API_KEY:
        return []
    
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=max_results,
            type='video',
            relevanceLanguage='en',
            safeSearch='strict'
        ).execute()
        
        videos = []
        for item in search_response.get('items', []):
            videos.append({
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'videoId': item['id']['videoId'],
                'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                'channelTitle': item['snippet']['channelTitle']
            })
        
        return videos
    except HttpError as e:
        print(f"YouTube API error: {e}")
        return []
    except Exception as e:
        print(f"Error searching videos: {e}")
        return []


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and extraction"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract text from file
        text_content = extract_text_from_file(filepath)
        
        if text_content:
            # Store in session
            session['document_content'] = text_content
            session['document_name'] = filename
            
            return jsonify({
                'success': True,
                'filename': filename,
                'content_length': len(text_content)
            })
        else:
            return jsonify({'error': 'Failed to extract text from file'}), 400
    
    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/summarize', methods=['POST'])
def summarize():
    """Generate summary of uploaded document"""
    content = session.get('document_content')
    
    if not content:
        return jsonify({'error': 'No document uploaded'}), 400
    
    system_prompt = """You are an expert at creating clear, comprehensive summaries of educational content.
Create a well-structured summary that captures the key concepts, main ideas, and important details.
Use headings and bullet points for clarity."""
    
    user_message = f"""Please create a comprehensive summary of the following document:

{content[:15000]}  # Limit to prevent token overflow

Include:
1. Main topics covered
2. Key concepts and definitions
3. Important points and takeaways
4. Any critical information"""
    
    summary = call_gemini(system_prompt, user_message)
    
    if summary:
        return jsonify({'summary': summary})
    else:
        return jsonify({'error': 'Failed to generate summary'}), 500


@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    """Generate quiz questions from document"""
    content = session.get('document_content')
    data = request.get_json()
    num_questions = data.get('num_questions', 10)
    difficulty = data.get('difficulty', 'medium')
    
    if not content:
        return jsonify({'error': 'No document uploaded'}), 400
    
    system_prompt = """You are an expert quiz creator. Generate high-quality multiple-choice questions 
that test understanding of key concepts. Return ONLY valid JSON with this exact structure:
{
  "questions": [
    {
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": 0,
      "explanation": "Explanation of the correct answer"
    }
  ]
}"""
    
    user_message = f"""Create {num_questions} {difficulty} difficulty multiple-choice questions based on this content:

{content[:12000]}

Requirements:
- Each question should have 4 options
- Include the index (0-3) of the correct answer
- Provide a clear explanation for each answer
- Questions should test comprehension, not just memorization
- Return ONLY the JSON, no additional text"""
    
    response = call_gemini(system_prompt, user_message, max_tokens=4000)
    
    if response:
        try:
            # Clean up response to ensure valid JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            quiz_data = json.loads(response)
            return jsonify(quiz_data)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response was: {response}")
            return jsonify({'error': 'Failed to parse quiz data'}), 500
    else:
        return jsonify({'error': 'Failed to generate quiz'}), 500


@app.route('/generate-mock-test', methods=['POST'])
def generate_mock_test():
    """Generate comprehensive mock test"""
    content = session.get('document_content')
    data = request.get_json()
    
    if not content:
        return jsonify({'error': 'No document uploaded'}), 400
    
    system_prompt = """You are an expert test creator. Create a comprehensive mock test with varied question types.
Return ONLY valid JSON with this structure:
{
  "test_name": "Test title",
  "duration_minutes": 60,
  "sections": [
    {
      "section_name": "Section name",
      "questions": [
        {
          "type": "mcq",
          "question": "Question text?",
          "options": ["A", "B", "C", "D"],
          "correct_answer": 0,
          "points": 2,
          "explanation": "Why this is correct"
        },
        {
          "type": "true_false",
          "question": "Statement to evaluate",
          "correct_answer": true,
          "points": 1,
          "explanation": "Explanation"
        },
        {
          "type": "short_answer",
          "question": "Question requiring brief answer?",
          "sample_answer": "Example correct answer",
          "points": 3
        }
      ]
    }
  ]
}"""
    
    user_message = f"""Create a comprehensive mock test based on this content:

{content[:12000]}

Include:
- 20-25 questions total
- Mix of multiple choice, true/false, and short answer questions
- Organize into 2-3 logical sections
- Assign appropriate point values
- Provide explanations for objective questions
- Return ONLY the JSON"""
    
    response = call_gemini(system_prompt, user_message, max_tokens=4000)
    
    if response:
        try:
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            test_data = json.loads(response)
            return jsonify(test_data)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return jsonify({'error': 'Failed to parse test data'}), 500
    else:
        return jsonify({'error': 'Failed to generate mock test'}), 500


@app.route('/generate-mindmap', methods=['POST'])
def generate_mindmap():
    """Generate mind map structure from document"""
    content = session.get('document_content')
    
    if not content:
        return jsonify({'error': 'No document uploaded'}), 400
    
    system_prompt = """You are an expert at creating hierarchical mind maps from educational content.
Create a structured mind map that shows relationships between concepts. Return ONLY valid JSON:
{
  "central_topic": "Main topic",
  "branches": [
    {
      "title": "Branch title",
      "subtopics": [
        {
          "title": "Subtopic",
          "points": ["Point 1", "Point 2"]
        }
      ]
    }
  ]
}"""
    
    user_message = f"""Create a comprehensive mind map structure from this content:

{content[:12000]}

The mind map should:
- Have a clear central topic
- Include 4-6 main branches
- Each branch should have 2-4 subtopics
- Each subtopic should have key points
- Return ONLY the JSON"""
    
    response = call_gemini(system_prompt, user_message, max_tokens=3000)
    
    if response:
        try:
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            mindmap_data = json.loads(response)
            return jsonify(mindmap_data)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return jsonify({'error': 'Failed to parse mind map data'}), 500
    else:
        return jsonify({'error': 'Failed to generate mind map'}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """AI chatbot for discussing the topic"""
    data = request.get_json()
    user_message = data.get('message', '')
    content = session.get('document_content', '')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get chat history from session
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    system_prompt = f"""You are a knowledgeable tutor helping a student understand educational content.
You have access to the following document content:

{content[:10000] if content else "No document uploaded yet."}

Answer the student's questions clearly and helpfully. Provide examples, explanations, and encourage learning.
If the question is not related to the document, you can still help with general educational topics."""
    
    response = call_gemini(system_prompt, user_message, max_tokens=2000)
    
    if response:
        # Store in chat history
        session['chat_history'].append({
            'user': user_message,
            'assistant': response,
            'timestamp': datetime.now().isoformat()
        })
        session.modified = True
        
        return jsonify({'response': response})
    else:
        return jsonify({'error': 'Failed to get response from AI'}), 500


@app.route('/search-videos', methods=['POST'])
def search_videos():
    """Search for educational videos on YouTube"""
    data = request.get_json()
    query = data.get('query', '')
    content = session.get('document_content', '')
    
    if not query and content:
        # Extract main topic from document
        system_prompt = "Extract the main topic or subject from this text in 3-5 words:"
        topic = call_gemini(system_prompt, content[:2000], max_tokens=50)
        query = topic.strip() if topic else ''
    
    if not query:
        return jsonify({'error': 'No search query provided'}), 400
    
    videos = search_youtube_videos(query + " tutorial explanation", max_results=8)
    
    return jsonify({'videos': videos, 'query': query})


@app.route('/clear-session', methods=['POST'])
def clear_session():
    """Clear session data"""
    session.clear()
    return jsonify({'success': True})

@app.route('/list-models')
def list_models():
    try:
        genai.configure(api_key=random.choice(GOOGLE_API_KEYS))
        models = [m.name for m in genai.list_models()]
        return jsonify({"available_models": models})
    except Exception as e:
        return jsonify({"error": str(e)})
    

if __name__ == '__main__':
    app.run(debug=os.environ.get("FLASK_DEBUG", "True").lower() == "true",
         host='0.0.0.0', 
            port=int(os.environ.get("PORT", 5000))
            )
