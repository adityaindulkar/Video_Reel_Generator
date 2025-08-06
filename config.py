import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class Config:
    # Basic App Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key-for-dev-only')
    
    # File Storage Paths
    UPLOAD_AUDIO_FOLDER = 'uploads/audio_input_reels'
    UPLOAD_TEXT_FOLDER = 'uploads/text_input_reels'
    OUTPUT_FOLDER = 'outputs'
    
    # Upload Limits
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # ElevenLabs Configuration (from environment variables)
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
    ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID')    
    
    # Ensure directories exist
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_AUDIO_FOLDER'], exist_ok=True)
        os.makedirs(app.config['UPLOAD_TEXT_FOLDER'], exist_ok=True)
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)