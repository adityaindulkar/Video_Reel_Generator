# Video Reel Generator
## Overview
A Flask-based web application that automatically generates video reels from images and audio/text inputs. Perfect for creating social media content, slideshows, and presentations.

## Tech Stack

### Backend
Python 3.8+   
Flask framework   
FFmpeg for video processing   
gTTS/ElevenLabs for text-to-speech   

### Frontend
HTML5, CSS3, JavaScript (Responsive design, File upload validation )    

## Key Features
### Input Options
**Audio + Images**: Upload audio files with matching images    
**Text + Images**: Convert text to speech and pair with images    
Custom duration control for each image    
**User-Specific File Management:**     
    **Isolated Storage:** Each user's uploaded content (images, audio files, and text-to-speech outputs) is stored in dedicated directories, segregated by user ID.    
    **Conflict Prevention:** Unique folder structures prevent file clashes during concurrent uploads/processing from multiple users.    
    **Clean Organization:** Automatically maintains separation between user-generated content for both input files (UPLOADS) and final outputs (OUTPUTS).    

### Processing Capabilities
Automatic audio/image duration matching    
Intelligent audio looping/trimming    
Image resizing and formatting (supports JPG, PNG, GIF)    
Smooth fade transitions between images    

### Output Features
HD video output (1080p)    
Optimized for social media    
Downloadable MP4 files    
Preview before download       

## Supported Formats
**Images**: JPG, JPEG, PNG, GIF    
**Audio**: MP3, WAV, OGG, M4A    
**Output**: MP4 (H.264/AAC)    

## Workflow
### Choose Input Type:   
Audio + Images    
Text + Images    

### Upload Content:    
For audio: Upload MP3/WAV file    
For text: Enter your script    
Upload multiple images   
Set display duration for each image       

### Generate & Preview:   
System processes inputs    
Preview the generated reel    
Download final MP4    

## Error Handling
### The application includes comprehensive error checking for:    
Invalid file formats    
Mismatched audio/image durations    
Corrupt media files    
API failures (with fallbacks)    

## Cleanup System    
### Automatic cleanup of:    
Old output files (>1 hour)    
Temporary upload folders    
Failed processing artifacts    
