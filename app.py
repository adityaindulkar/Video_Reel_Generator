import os
import subprocess, traceback
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import ffmpeg
import requests
from datetime import datetime, timedelta
import json
from config import Config
from gtts import gTTS
import shutil
from PIL import Image


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'your_secret_key_here'  # Required for flash messages

# Ensure upload and output directories exist
os.makedirs(app.config['UPLOAD_AUDIO_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_TEXT_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def validate_file_extension(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/audio-input', methods=['GET', 'POST'])
def audio_input():
    if request.method == 'POST':
        try:
            # Debug: Print form data
            print("\n=== Received form data ===")
            print("Audio file:", request.files.get('audio').filename if 'audio' in request.files else None)
            print("Durations:", request.form.getlist('durations'))
            print("Files:", [f.filename for f in request.files.getlist('images') if f.filename])

            # Validate inputs
            if 'audio' not in request.files:
                flash('No audio file uploaded', 'error')
                return redirect(request.url)
                
            audio_file = request.files['audio']
            if audio_file.filename == '':
                flash('No selected audio file', 'error')
                return redirect(request.url)
                
            if not validate_file_extension(audio_file.filename, ['mp3', 'wav', 'ogg', 'm4a']):  # Added m4a support
                flash('Invalid audio file type', 'error')
                return redirect(request.url)
                
            if 'images' not in request.files:
                flash('No images uploaded', 'error')
                return redirect(request.url)
                
            images = request.files.getlist('images')
            if not any(img.filename != '' for img in images):
                flash('No selected images', 'error')
                return redirect(request.url)

            # Create unique folder for this reel
            reel_id = datetime.now().strftime("%Y%m%d%H%M%S")
            reel_folder = os.path.join(app.config['UPLOAD_AUDIO_FOLDER'], reel_id)
            images_folder = os.path.join(reel_folder, 'images')
            os.makedirs(images_folder, exist_ok=True)
            print("\n=== Created directories ===")
            print("Reel folder:", reel_folder)
            print("Images folder:", images_folder)
            
            # Save audio file with proper extension handling
            audio_filename = secure_filename(audio_file.filename)
            audio_ext = audio_filename.rsplit('.', 1)[1].lower() if '.' in audio_filename else ''
            audio_save_name = f"audio.{audio_ext}" if audio_ext else "audio"
            audio_path = os.path.join(reel_folder, audio_save_name)
            
            print("\n=== Saving audio ===")
            try:
                audio_file.save(audio_path)
                print("Audio saved at:", audio_path)
                if not os.path.exists(audio_path):
                    raise RuntimeError("Audio file was not created")
            except Exception as e:
                print("Failed to save audio:", str(e))
                raise
            
            # Save images with validation
            image_paths = []
            print("\n=== Processing images ===")
            for i, image in enumerate(images):
                if image.filename == '':
                    continue
                    
                if not validate_file_extension(image.filename, ['jpg', 'jpeg', 'png', 'gif', 'JPG']):  # Added uppercase JPG
                    print(f"Skipping invalid file: {image.filename}")
                    continue
                
                img_ext = image.filename.rsplit('.', 1)[1].lower() if '.' in image.filename else ''
                img_save_name = f"image_{i}.{img_ext}" if img_ext else f"image_{i}"
                img_path = os.path.join(images_folder, img_save_name)
                
                image.save(img_path)
                print(f"Saved image: {img_path}")
                
                # Store path with forward slashes for consistency
                stored_path = img_path.replace('\\', '/')
                if not os.path.exists(img_path):
                    raise RuntimeError(f"Failed to save image: {img_path}")
                image_paths.append(stored_path)
                
            if not image_paths:
                flash('No valid images uploaded', 'error')
                return redirect(request.url)
            
            # Validate durations
            durations = request.form.getlist('durations')
            if len(durations) != len(image_paths):
                flash('Number of durations does not match number of images', 'error')
                return redirect(request.url)
            
            try:
                durations = [float(d) for d in durations]
                if any(d <= 0 for d in durations):
                    raise ValueError("Durations must be positive")
            except ValueError:
                flash('Invalid duration values', 'error')
                return redirect(request.url)
            
            # Store paths with forward slashes in config
            config = {
                'image_paths': image_paths,
                'audio_path': audio_path.replace('\\', '/'),
                'durations': durations,
                'type': 'audio_input'
            }
            
            config_path = os.path.join(reel_folder, 'config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            print("\n=== Saved config ===")
            print("Config path:", config_path)
            print("Config content:", json.dumps(config, indent=2))
            
            # Generate reel
            print("\n=== Generating reel ===")
            try:
                output_path = generate_reel(reel_id, config)
                output_path = os.path.normpath(output_path)  # Normalize path
                print("Generated output path:", output_path)
                
                if not os.path.exists(output_path):
                    raise RuntimeError("Output video was not created")
                
                print("Reel successfully generated!")
                flash('Reel successfully created!', 'success')
                return redirect(url_for('preview', reel_id=reel_id))
            except Exception as e:
                print("Reel generation failed:", str(e))
                print(traceback.format_exc())
                raise
            
        except Exception as e:
            print("\n=== ERROR ===")
            print(traceback.format_exc())
            flash(f'Error: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('audio_input.html')

@app.route('/text-input', methods=['GET', 'POST'])
def text_input():
    if request.method == 'POST':
        try:
            # Debug: Print form data
            print("\n=== Received form data ===")
            print("Text:", request.form.get('text'))
            print("Durations:", request.form.getlist('durations'))
            print("Files:", [f.filename for f in request.files.getlist('images') if f.filename])

            # Validate text input
            text = request.form.get('text', '').strip()
            if not text:
                flash('No text provided', 'error')
                return redirect(request.url)
                
            if 'images' not in request.files:
                flash('No images uploaded', 'error')
                return redirect(request.url)
                
            images = request.files.getlist('images')
            if not any(img.filename != '' for img in images):
                flash('No selected images', 'error')
                return redirect(request.url)

            # Create unique folder for this reel
            reel_id = datetime.now().strftime("%Y%m%d%H%M%S")
            reel_folder = os.path.join(app.config['UPLOAD_TEXT_FOLDER'], reel_id)
            os.makedirs(reel_folder, exist_ok=True)
            os.makedirs(os.path.join(reel_folder, 'images'), exist_ok=True)
            
            # Generate audio from text
            audio_path = os.path.join(reel_folder, 'generated_audio.mp3')
            print("\n=== Generating audio ===")
            try:
                generate_audio_from_text(text, audio_path)
                print("Audio generated at:", audio_path)
                if not os.path.exists(audio_path):
                    raise RuntimeError("Audio file was not created")
            except Exception as e:
                print("Audio generation failed:", str(e))
                raise
            
            # Save images with validation
            image_paths = []
            print("\n=== Processing images ===")
            for i, image in enumerate(images):
                if image.filename == '':
                    continue
                if not validate_file_extension(image.filename, ['jpg', 'jpeg', 'png', 'gif']):
                    print(f"Skipping invalid file: {image.filename}")
                    continue
                
                img_filename = secure_filename(image.filename)
                img_path = os.path.join(reel_folder, 'images', f"{i}_{img_filename}")
                image.save(img_path)
                print(f"Saved image: {img_path}")
                if not os.path.exists(img_path):
                    raise RuntimeError(f"Failed to save image: {img_path}")
                image_paths.append(img_path)
                
            if not image_paths:
                flash('No valid images uploaded', 'error')
                return redirect(request.url)
            
            # Validate durations
            durations = request.form.getlist('durations')
            if len(durations) != len(image_paths):
                flash('Number of durations does not match number of images', 'error')
                return redirect(request.url)
            
            try:
                durations = [float(d) for d in durations]
                if any(d <= 0 for d in durations):
                    raise ValueError("Durations must be positive")
            except ValueError:
                flash('Invalid duration values', 'error')
                return redirect(request.url)
            
            config = {
                'image_paths': image_paths,
                'audio_path': audio_path,
                'durations': durations,
                'type': 'text_input',
                'text': text
            }
            
            config_path = os.path.join(reel_folder, 'config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f)
            print("\n=== Saved config ===")
            print("Config path:", config_path)
            
            # Generate reel
            print("\n=== Generating reel ===")
            try:
                output_path = generate_reel(reel_id, config)
                print("Expected output path:", output_path)
                
                if not os.path.exists(output_path):
                    raise RuntimeError("Output video was not created")
                
                print("Reel successfully generated!")
                flash('Reel successfully created!', 'success')
                return redirect(url_for('preview', reel_id=reel_id))
            except Exception as e:
                print("Reel generation failed:", str(e))
                raise
            
        except Exception as e:
            print("\n=== ERROR ===")
            print(traceback.format_exc())
            flash(f'Error: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('text_input.html')

@app.route('/preview/<reel_id>')
def preview(reel_id):
    # Verify the reel exists
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{reel_id}.mp4")
    if not os.path.exists(output_path):
        flash('Reel not found', 'error')
        return redirect(url_for('index'))
    
    # Create a URL-accessible path for the video
    video_url = url_for('download', reel_id=reel_id)

    paths_to_update = [
        os.path.join(app.config['OUTPUT_FOLDER'], f"{reel_id}.mp4"),
        os.path.join(app.config['UPLOAD_AUDIO_FOLDER'], reel_id),
        os.path.join(app.config['UPLOAD_TEXT_FOLDER'], reel_id)
    ]
    
    for path in paths_to_update:
        if os.path.exists(path):
            os.utime(path, None)  # Update timestamp to "now"
    
    return render_template('preview.html', 
                         reel_id=reel_id,
                         video_url=video_url)

@app.route('/download/<reel_id>')
def download(reel_id):
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{reel_id}.mp4")
    if not os.path.exists(output_path):
        flash('Reel not found', 'error')
        return redirect(url_for('index'))
    
    os.utime(output_path, None)
    return send_from_directory(
        app.config['OUTPUT_FOLDER'],
        f"{reel_id}.mp4",
        as_attachment=True
    )

def generate_audio_from_text(text, output_path):
    """Generate audio from text using ElevenLabs API with gTTS fallback"""
    try:
        # Try ElevenLabs first if configured
        if app.config.get('ELEVENLABS_API_KEY') and app.config.get('ELEVENLABS_VOICE_ID'):
            headers = {
                "xi-api-key": app.config['ELEVENLABS_API_KEY'],
                "Content-Type": "application/json"
            }
            
            data = {
                "text": text,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{app.config['ELEVENLABS_VOICE_ID']}",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return
        
        # Fallback to gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(output_path)
        
    except Exception as e:
        # If ElevenLabs fails, use gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(output_path)
        raise Exception(f"Audio generation issue: {str(e)}")
    
def get_audio_duration(audio_path):
    """More robust duration detection with FFprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        result = subprocess.run(cmd, check=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
        return float(result.stdout.strip())
    except Exception as e:
        raise RuntimeError(f"Failed to get audio duration: {str(e)}")
    
def generate_reel(reel_id, config):
    """Generate video reel with bulletproof image handling and FFmpeg processing"""
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{reel_id}.mp4")
    cleaned_folder = os.path.join(app.config['OUTPUT_FOLDER'], "cleaned_images")
    os.makedirs(cleaned_folder, exist_ok=True)

    try:
        print("\n=== Validating and preprocessing images ===")
        cleaned_image_paths = []
        
        for idx, img_path in enumerate(config['image_paths']):
            if not os.path.exists(img_path):
                raise FileNotFoundError(f"Image not found: {img_path}")
            
            try:
                # First verify the file is readable and valid
                try:
                    with open(img_path, 'rb') as f:
                        Image.open(f).verify()  # Verify without keeping file open
                except Exception as verify_error:
                    raise RuntimeError(f"Image verification failed: {verify_error}")
                
                # Now process with explicit file handling
                with open(img_path, 'rb') as f:
                    try:
                        img = Image.open(f)
                        # Force load image data into memory immediately
                        img.load()
                        
                        if img is None:
                            raise RuntimeError("Image.open() returned None - corrupt file?")
                            
                        # Convert to RGB if needed
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Process dimensions
                        w, h = img.size
                        w = (w + 1) // 2 * 2
                        h = (h + 1) // 2 * 2
                        
                        # Create new image in memory to avoid file pointer issues
                        processed_img = Image.new('RGB', (w, h))
                        processed_img.paste(img.resize((w, h)))
                        
                        cleaned_path = os.path.join(cleaned_folder, f"img_{idx}.jpg")
                        processed_img.save(cleaned_path, quality=95, subsampling=0)
                        cleaned_image_paths.append(cleaned_path)
                        print(f"✅ Processed image {idx+1}: {w}x{h}")
                        
                    except Exception as img_error:
                        raise RuntimeError(f"Image processing failed: {img_error}")
                        
            except Exception as e:
                print(f"❌ Failed to process image {img_path}: {str(e)}")
                if 'NoneType' in str(e):
                    print("ℹ️ Tip: This usually indicates a corrupt image file or unsupported format")
                raise RuntimeError(f"Image processing error: {str(e)}")

        # Audio processing (unchanged)
        if not os.path.exists(config['audio_path']):
            raise FileNotFoundError(f"Audio file not found: {config['audio_path']}")

        audio_duration = get_audio_duration(config['audio_path'])
        total_image_duration = sum(config['durations'])
        print(f"\nAudio duration: {audio_duration:.2f}s | Total image duration: {total_image_duration:.2f}s")

        if audio_duration < total_image_duration:
            loops = int(total_image_duration / audio_duration) + 1
            audio_input = ffmpeg.input(config['audio_path'], stream_loop=loops)
            audio = audio_input.filter('atrim', duration=total_image_duration)
            print(f"🔁 Looped audio {loops}x to match duration")
        elif audio_duration > total_image_duration + 1.0:
            audio_input = ffmpeg.input(config['audio_path'])
            audio = audio_input.filter('atrim', duration=total_image_duration).filter('afade', t='out', st=total_image_duration - 1, d=1)
            print(f"✂️ Trimmed audio from {audio_duration:.2f}s to {total_image_duration:.2f}s")
        else:
            audio = ffmpeg.input(config['audio_path'])
            print("✅ Audio duration matches perfectly")

        TARGET_WIDTH, TARGET_HEIGHT = 1920, 1080
        video_streams = []

        for idx, (img_path, duration) in enumerate(zip(cleaned_image_paths, config['durations'])):
            try:
                print(f"\nProcessing cleaned image {idx+1}: {os.path.basename(img_path)} ({duration}s)")
                
                # Modified input with explicit duration
                stream = ffmpeg.input(img_path, framerate=24, loop=1, t=duration)
                
                # Simplified scaling and padding
                stream = stream.filter('scale', 
                                    TARGET_WIDTH, TARGET_HEIGHT, 
                                    force_original_aspect_ratio='decrease')
                stream = stream.filter('pad',
                                    TARGET_WIDTH, TARGET_HEIGHT,
                                    '(ow-iw)/2', '(oh-ih)/2',
                                    color='black')
                
                # Ensure even dimensions
                stream = stream.filter('scale', 'ceil(iw/2)*2', 'ceil(ih/2)*2')
                stream = stream.filter('setsar', '1')
                
                # Fade effects
                if duration >= 1.0:
                    if idx == 0:
                        stream = stream.filter('fade', t='in', st=0, d=0.5)
                    if idx == len(cleaned_image_paths) - 1:
                        stream = stream.filter('fade', t='out', st=duration - 0.5, d=0.5)
                else:
                    print(f"⚠️ Skipping fade: duration too short ({duration}s)")
                
                stream = stream.filter('format', 'yuv420p')
                video_streams.append(stream)

            except Exception as e:
                print(f"❌ Error processing image {img_path}: {e}")
                raise

        video = ffmpeg.concat(*video_streams, v=1, a=0)

        ffmpeg_cmd = (
            ffmpeg.output(
                video, audio, output_path,
                vcodec='libx264',
                acodec='aac',
                preset='fast',
                movflags='+faststart',
                pix_fmt='yuv420p',
                crf=23,
                **{'b:a': '192k'}
            )
            .global_args('-loglevel', 'error')
            .overwrite_output()
        )

        print("\n=== FFmpeg Command ===")
        print(" ".join(ffmpeg_cmd.compile()))

        ffmpeg_cmd.run()

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("Output file was not created or is empty")

        print(f"\n🎉 Successfully generated: {output_path}")
        return output_path

    except ffmpeg.Error as e:
        print("❌ FFmpeg stderr:\n", e.stderr.decode('utf8', errors='ignore') if e.stderr else "No stderr")
        raise RuntimeError("FFmpeg processing failed.")
    except Exception as e:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise RuntimeError(f"Reel generation error: {str(e)}")
    
def cleanup_old_files(hours=1):
    """Clean both output files AND uploaded folders older than X hours"""
    cutoff = datetime.now() - timedelta(hours=hours)
    
    # 1. Clean OUTPUT_FOLDER (*.mp4 files)
    output_folder = app.config['OUTPUT_FOLDER']
    if os.path.exists(output_folder):
        for filename in os.listdir(output_folder):
            if filename.endswith('.mp4'):
                file_path = os.path.join(output_folder, filename)
                try:
                    if datetime.fromtimestamp(os.path.getmtime(file_path)) < cutoff:
                        os.remove(file_path)
                        print(f"🧹 Deleted output: {file_path}")
                except Exception as e:
                    print(f"❌ Error deleting output {file_path}: {e}")

    # 2. Clean UPLOAD_AUDIO_FOLDER (individual reel folders)
    audio_folder = app.config['UPLOAD_AUDIO_FOLDER']
    if os.path.exists(audio_folder):
        for reel_id in os.listdir(audio_folder):
            reel_path = os.path.join(audio_folder, reel_id)
            try:
                if datetime.fromtimestamp(os.path.getmtime(reel_path)) < cutoff:
                    shutil.rmtree(reel_path)
                    print(f"🧹 Deleted audio reel: {reel_path}")
            except Exception as e:
                print(f"❌ Error deleting audio reel {reel_path}: {e}")

    # 3. Clean UPLOAD_TEXT_FOLDER (individual reel folders)
    text_folder = app.config['UPLOAD_TEXT_FOLDER']
    if os.path.exists(text_folder):
        for reel_id in os.listdir(text_folder):
            reel_path = os.path.join(text_folder, reel_id)
            try:
                if datetime.fromtimestamp(os.path.getmtime(reel_path)) < cutoff:
                    shutil.rmtree(reel_path)
                    print(f"🧹 Deleted text reel: {reel_path}")
            except Exception as e:
                print(f"❌ Error deleting text reel {reel_path}: {e}")


print("🚀 Starting cleanup...")
cleanup_old_files(hours=1)  # Change number to adjust retention time
print("✅ Cleanup complete")
    
if __name__ == '__main__':
    app.run(debug=True)