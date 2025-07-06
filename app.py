#!/usr/bin/env python3
"""
AI-Powered Educational Presentation System - Main Flask Application
"""

import os
import json
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import threading
import time

# Import custom modules
from modules.course_generator import CourseGenerator
from modules.presentation_planner import PresentationPlanner
from modules.slide_generator import SlideGenerator
from modules.image_manager import ImageManager
from modules.presentation_builder import PresentationBuilder
from modules.audio_manager import AudioManager
from modules.file_manager import FileManager
from modules.conversation_manager import ConversationManager
from modules.progress_tracker import ProgressTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce verbosity of external libraries
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
CORS(app)

# Configure SocketIO for long-running operations with extended timeouts
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    ping_timeout=300,  # 5 minutes timeout for pings
    ping_interval=15,  # Send ping every 15 seconds
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    max_http_buffer_size=10000000,  # 10MB buffer for large messages
    allow_upgrades=True,
    transports=['websocket', 'polling']
)

# Initialize managers with file_manager for session-based organization
file_manager = FileManager()
course_generator = CourseGenerator(file_manager=file_manager)
presentation_planner = PresentationPlanner(file_manager=file_manager)
slide_generator = SlideGenerator(file_manager=file_manager)
image_manager = ImageManager(file_manager=file_manager)
presentation_builder = PresentationBuilder(file_manager=file_manager)
audio_manager = AudioManager(file_manager=file_manager)
conversation_manager = ConversationManager(file_manager=file_manager)

# Global state for tracking generation progress
active_sessions = {}
progress_trackers = {}  # Enhanced progress trackers by session_id

@app.route('/')
def index():
    """Root endpoint returning system status"""
    return jsonify({
        'status': 'running',
        'system': 'AI-Powered Educational Presentation System',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/test-validation', methods=['POST'])
def test_validation():
    """Test endpoint to validate request format"""
    try:
        data = request.json
        logger.info(f"Test validation request: {data}")
        
        # Test the same validation logic
        required_fields = {
            'topic': 'topic',
            'complexity': 'complexity', 
            'duration': 'duration',
            'learning_style': ['learning_style', 'learningStyle']  # Accept both formats
        }
        
        missing_fields = []
        for field, field_variants in required_fields.items():
            if isinstance(field_variants, list):
                # Check if any variant exists
                if not any(variant in data for variant in field_variants):
                    missing_fields.append(f"{field} (or {', '.join(field_variants)})")
            else:
                # Single field name
                if field_variants not in data:
                    missing_fields.append(field_variants)
        
        if missing_fields:
            return jsonify({
                'valid': False,
                'missing_fields': missing_fields,
                'received_data': data
            }), 400
        
        return jsonify({
            'valid': True,
            'message': 'All required fields present',
            'received_data': data
        })
        
    except Exception as e:
        logger.error(f"Error in test validation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-course', methods=['POST'])
def generate_course():
    """Generate a complete course presentation"""
    try:
        data = request.json
        logger.info(f"Received course generation request: {data}")
        session_id = data.get('session_id', str(time.time()))
        
        # Validate required fields with flexible naming
        required_fields = {
            'topic': 'topic',
            'complexity': 'complexity', 
            'duration': 'duration',
            'learning_style': ['learning_style', 'learningStyle']  # Accept both formats
        }
        
        for field, field_variants in required_fields.items():
            if isinstance(field_variants, list):
                # Check if any variant exists
                if not any(variant in data for variant in field_variants):
                    return jsonify({'error': f'Missing required field: {field} (or {", ".join(field_variants)})'}), 400
            else:
                # Single field name
                if field_variants not in data:
                    return jsonify({'error': f'Missing required field: {field_variants}'}), 400
        
        # Store session data
        active_sessions[session_id] = {
            'status': 'initializing',
            'progress': 0,
            'stage': 'Starting course generation',
            'data': data,
            'start_time': time.time()
        }
        
        # Initialize enhanced progress tracker
        progress_trackers[session_id] = ProgressTracker(session_id)
        
        # Start generation in background thread
        thread = threading.Thread(
            target=_generate_course_async,
            args=(session_id, data)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'session_id': session_id,
            'status': 'started',
            'message': 'Course generation started'
        })
        
    except Exception as e:
        logger.error(f"Error starting course generation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/status', methods=['GET'])
def get_session_status(session_id):
    """Get the current status of a generation session"""
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify(active_sessions[session_id])

@app.route('/api/presentations', methods=['GET'])
def list_presentations():
    """List all saved presentations"""
    try:
        presentations = file_manager.list_presentations()
        return jsonify(presentations)
    except Exception as e:
        logger.error(f"Error listing presentations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/presentation/<presentation_id>', methods=['GET'])
def get_presentation(presentation_id):
    """Get a specific presentation file"""
    try:
        file_path = file_manager.get_presentation_path(presentation_id)
        if not file_path.exists():
            return jsonify({'error': 'Presentation not found'}), 404
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error retrieving presentation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/presentation/<presentation_id>/metadata', methods=['GET'])
def get_presentation_metadata(presentation_id):
    """Get metadata for a specific presentation"""
    try:
        metadata = file_manager.get_presentation_metadata(presentation_id)
        return jsonify(metadata)
    except Exception as e:
        logger.error(f"Error retrieving metadata: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tts/synthesize', methods=['POST'])
def synthesize_speech():
    """Synthesize speech from text"""
    try:
        data = request.json
        text = data.get('text', '')
        voice = data.get('voice', 'default')
        speed = data.get('speed', 1.0)
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Note: For single TTS calls, we don't have session context here
        # This endpoint could be enhanced to accept session_id as optional parameter
        audio_file = audio_manager.synthesize_speech(text, voice, speed)
        return send_file(audio_file, mimetype='audio/wav')
        
    except Exception as e:
        logger.error(f"Error synthesizing speech: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stt/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio to text"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        transcription = audio_manager.transcribe_audio(audio_file)
        
        return jsonify({'transcription': transcription})
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tts/voices', methods=['GET'])
def get_available_voices():
    """Get list of available TTS voices"""
    try:
        voices = audio_manager.available_voices
        return jsonify({
            'voices': voices,
            'default_voice': voices[0]['id'] if voices else 'default'
        })
    except Exception as e:
        logger.error(f"Error getting TTS voices: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET'])
def get_user_settings():
    """Get user settings from local storage"""
    try:
        settings_file = Path('data/settings.json')
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            # Default settings
            settings = {
                'tts': {
                    'voice': 'default',
                    'speed': 1.0,
                    'volume': 0.8
                },
                'presentation': {
                    'theme': 'dark',
                    'layout': 'modern',
                    'animations': True,
                    'auto_advance': True
                },
                'course_defaults': {
                    'complexity': 'intermediate',
                    'duration': '45-60 minutes',
                    'learning_style': 'visual',
                    'content_density': 'medium',
                    'batch_size': 5
                },
                'advanced': {
                    'prerequisites_handling': 'auto',
                    'specialized_focus': 'balanced',
                    'presentation_style': 'professional'
                }
            }
        
        return jsonify(settings)
    except Exception as e:
        logger.error(f"Error getting user settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def save_user_settings():
    """Save user settings to local storage"""
    try:
        settings = request.json
        settings_file = Path('data/settings.json')
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        return jsonify({'message': 'Settings saved successfully'})
    except Exception as e:
        logger.error(f"Error saving user settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/course-templates', methods=['GET'])
def get_course_templates():
    """Get available course templates"""
    try:
        templates = [
            {
                'id': 'math_fundamentals',
                'name': 'Mathematics Fundamentals',
                'description': 'Basic mathematical concepts and operations',
                'category': 'mathematics',
                'duration': '45-60 minutes',
                'complexity': 'beginner',
                'prerequisites': [],
                'focus_areas': ['arithmetic', 'algebra', 'geometry']
            },
            {
                'id': 'programming_intro',
                'name': 'Introduction to Programming',
                'description': 'Programming basics with practical examples',
                'category': 'computer_science',
                'duration': '60+ minutes',
                'complexity': 'beginner',
                'prerequisites': [],
                'focus_areas': ['syntax', 'logic', 'problem_solving']
            },
            {
                'id': 'history_overview',
                'name': 'Historical Overview',
                'description': 'Comprehensive historical analysis',
                'category': 'history',
                'duration': '45-60 minutes',
                'complexity': 'intermediate',
                'prerequisites': ['basic_chronology'],
                'focus_areas': ['timeline', 'causes', 'effects']
            },
            {
                'id': 'science_exploration',
                'name': 'Scientific Exploration',
                'description': 'Scientific method and discoveries',
                'category': 'science',
                'duration': '45-60 minutes',
                'complexity': 'intermediate',
                'prerequisites': ['basic_math'],
                'focus_areas': ['hypothesis', 'experimentation', 'analysis']
            },
            {
                'id': 'business_basics',
                'name': 'Business Fundamentals',
                'description': 'Essential business concepts and practices',
                'category': 'business',
                'duration': '60+ minutes',
                'complexity': 'intermediate',
                'prerequisites': [],
                'focus_areas': ['strategy', 'marketing', 'finance']
            }
        ]
        
        return jsonify({'templates': templates})
    except Exception as e:
        logger.error(f"Error getting course templates: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/ask', methods=['POST'])
def ask_question():
    """Ask a question about the current presentation"""
    try:
        data = request.json
        question = data.get('question', '')
        session_id = data.get('session_id', '')
        slide_context = data.get('slide_context', {})
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Extract slide context for conversation manager
        slide_transcript = slide_context.get('transcript', '')
        slide_screenshot = slide_context.get('screenshot', None)
        slide_image_url = slide_context.get('slide_image_url', None)
        
        response = conversation_manager.ask_question(
            session_id=session_id,
            question=question,
            slide_screenshot=slide_screenshot,
            slide_transcript=slide_transcript,
            slide_image_url=slide_image_url
        )
        
        return jsonify({'response': response})
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Course/presentation endpoints to match frontend API expectations
@app.route('/api/course/<session_id>', methods=['GET'])
def get_course(session_id):
    """Get course data by session ID"""
    try:
        # First check if it's in active sessions
        if session_id in active_sessions:
            session_data = active_sessions[session_id]
            if session_data['status'] != 'completed':
                return jsonify({'error': 'Course generation not completed'}), 400
            return jsonify(session_data.get('result', {}))
        
        # If not in active sessions, check persistent storage using file_manager
        course_data = file_manager.load_course_session(session_id)
        if course_data:
            
            # Transform the data for frontend consumption
            transformed_data = _transform_course_data_for_frontend(course_data)
            return jsonify(transformed_data)
        
        return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        logger.error(f"Error retrieving course: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses', methods=['GET'])
def list_courses():
    """List all completed courses"""
    try:
        courses = []
        
        # Load courses from persistent storage using file_manager
        stored_courses = file_manager.session_index
        if stored_courses:
            
            for session_id, course_data in stored_courses.items():
                course_info = {
                    'session_id': session_id,
                    'course_title': course_data.get('course_title', 'Untitled Course'),
                    'topic': course_data.get('topic', ''),
                    'created_at': course_data.get('created_at'),
                    'status': course_data.get('status', 'completed'),
                    'complexity': course_data.get('complexity', 'intermediate'),
                    'duration': course_data.get('duration', ''),
                    'slide_count': course_data.get('slide_count', 0),
                    'file_size': course_data.get('file_size', 0),
                    'tags': course_data.get('tags', [])
                }
                courses.append(course_info)
        
        # Also include active sessions that are completed
        for session_id, session_data in active_sessions.items():
            if session_data['status'] == 'completed':
                # Check if this session is already in stored courses
                if not any(c['session_id'] == session_id for c in courses):
                    course_info = {
                        'session_id': session_id,
                        'course_title': session_data.get('data', {}).get('topic', 'Untitled Course'),
                        'topic': session_data.get('data', {}).get('topic', ''),
                        'created_at': session_data.get('start_time'),
                        'status': session_data['status'],
                        'complexity': session_data.get('data', {}).get('complexity', 'intermediate'),
                        'duration': session_data.get('data', {}).get('duration', ''),
                        'slide_count': 0,
                        'file_size': 0,
                        'tags': []
                    }
                    courses.append(course_info)
        
        # Sort by created_at descending
        sort_by = request.args.get('sort_by', 'created_at')
        if sort_by == 'created_at':
            def safe_sort_key(x):
                created_at = x.get('created_at', '')
                if isinstance(created_at, (int, float)):
                    # Convert timestamp to string for consistent sorting
                    return str(created_at)
                elif isinstance(created_at, str):
                    return created_at
                else:
                    return ''
            courses.sort(key=safe_sort_key, reverse=True)
        elif sort_by == 'title':
            courses.sort(key=lambda x: x.get('course_title', '').lower())
        elif sort_by == 'topic':
            courses.sort(key=lambda x: x.get('topic', '').lower())
        elif sort_by == 'size':
            courses.sort(key=lambda x: x.get('file_size', 0), reverse=True)
        
        return jsonify(courses)
    except Exception as e:
        logger.error(f"Error listing courses: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/course/<session_id>', methods=['DELETE'])
def delete_course(session_id):
    """Delete a course by session ID"""
    try:
        deleted = False
        
        # Remove from active sessions if present
        if session_id in active_sessions:
            del active_sessions[session_id]
            deleted = True
        
        # Remove from persistent storage using file_manager
        deleted = file_manager.delete_course_session(session_id)
        
        if deleted:
            return jsonify({'message': 'Course deleted successfully'})
        else:
            return jsonify({'error': 'Course not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting course: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/course/<session_id>/export', methods=['GET'])
def export_course(session_id):
    """Export course in specified format"""
    try:
        format_type = request.args.get('format', 'zip')
        
        # Check if course exists in active sessions or persistent storage
        course_exists = False
        if session_id in active_sessions:
            session_data = active_sessions[session_id]
            if session_data['status'] != 'completed':
                return jsonify({'error': 'Course generation not completed'}), 400
            course_exists = True
        else:
            # Check persistent storage using file_manager
            course_data = file_manager.load_course_session(session_id)
            if course_data:
                course_exists = True
        
        if not course_exists:
            return jsonify({'error': 'Session not found'}), 404
        
        # For now, return a placeholder response
        return jsonify({'message': f'Export in {format_type} format not yet implemented'}), 501
        
    except Exception as e:
        logger.error(f"Error exporting course: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Enhanced Progress Tracking Endpoints
@app.route('/api/session/<session_id>/progress/detailed', methods=['GET'])
def get_detailed_progress(session_id):
    """Get detailed progress information for a session"""
    try:
        if session_id not in progress_trackers:
            return jsonify({'error': 'Progress tracker not found for session'}), 404
        
        tracker = progress_trackers[session_id]
        detailed_status = tracker.get_current_status()
        
        return jsonify(detailed_status)
        
    except Exception as e:
        logger.error(f"Error getting detailed progress: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/progress/statistics', methods=['GET'])
def get_progress_statistics(session_id):
    """Get processing statistics for a session"""
    try:
        if session_id not in progress_trackers:
            return jsonify({'error': 'Progress tracker not found for session'}), 404
        
        tracker = progress_trackers[session_id]
        status = tracker.get_current_status()
        
        return jsonify({
            'session_id': session_id,
            'statistics': status['statistics'],
            'timing': status['timing'],
            'performance_metrics': {
                'slides_per_minute': status['statistics']['avg_slides_per_minute'],
                'images_per_minute': status['statistics']['avg_images_per_minute'],
                'processing_speed': status['statistics']['processing_speed'],
                'api_efficiency': {
                    'total_calls': status['statistics']['api_calls_made'],
                    'avg_response_time': status['statistics']['avg_response_time'],
                    'tokens_per_second': (
                        status['statistics']['total_tokens_used'] / max(status['timing']['elapsed_time_seconds'], 1)
                    )
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting progress statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/progress/stages', methods=['GET'])
def get_progress_stages(session_id):
    """Get detailed stage information for a session"""
    try:
        if session_id not in progress_trackers:
            return jsonify({'error': 'Progress tracker not found for session'}), 404
        
        tracker = progress_trackers[session_id]
        status = tracker.get_current_status()
        
        return jsonify({
            'session_id': session_id,
            'current_stage': status['current_stage'],
            'all_stages': status['stages_summary'],
            'progress_breakdown': [
                {
                    'stage_name': stage['name'],
                    'completed': stage['completed'],
                    'progress_percentage': stage['progress'],
                    'status': 'completed' if stage['completed'] else ('in_progress' if stage['progress'] > 0 else 'pending')
                }
                for stage in status['stages_summary']
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting progress stages: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/logs', methods=['GET'])
def get_session_logs(session_id):
    """Get AI interaction logs for debugging"""
    try:
        logs = file_manager.get_session_logs(session_id)
        
        # Process logs for frontend consumption
        processed_logs = []
        for log in logs:
            processed_log = {
                'timestamp': log.get('timestamp'),
                'stage': log.get('stage'),
                'model_name': log.get('model_name'),
                'processing_time': log.get('processing_time_seconds'),
                'request_size': log.get('metadata', {}).get('request_size_chars', 0),
                'response_size': log.get('metadata', {}).get('response_size_chars', 0),
                'tokens_per_second': log.get('metadata', {}).get('tokens_per_second', 0),
                'tokens_used': log.get('response', {}).get('usage', {}).get('total_tokens', 0),
                'success': log.get('response', {}).get('finish_reason') == 'STOP'
            }
            processed_logs.append(processed_log)
        
        # Calculate summary statistics
        total_calls = len(processed_logs)
        avg_processing_time = sum(log['processing_time'] for log in processed_logs) / max(total_calls, 1)
        total_tokens = sum(log['tokens_used'] for log in processed_logs)
        
        return jsonify({
            'session_id': session_id,
            'logs': processed_logs,
            'summary': {
                'total_api_calls': total_calls,
                'average_processing_time': round(avg_processing_time, 3),
                'total_tokens_used': total_tokens,
                'stages_covered': list(set(log['stage'] for log in processed_logs)),
                'success_rate': sum(1 for log in processed_logs if log['success']) / max(total_calls, 1) * 100
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting session logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/transcripts', methods=['GET'])
def get_session_transcripts(session_id):
    """Get transcript files for a session"""
    try:
        # Use session-based transcript directory
        subdirs = file_manager.get_session_subdirs(session_id)
        transcript_dir = subdirs['transcripts']
        
        if not transcript_dir.exists():
            return jsonify({'error': 'No transcripts found for session'}), 404
        
        transcripts = []
        for transcript_file in sorted(transcript_dir.glob('*.txt')):
            try:
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract slide number from filename
                slide_num = int(transcript_file.stem.split('_')[1])
                
                transcripts.append({
                    'slide_number': slide_num,
                    'filename': transcript_file.name,
                    'content': content,
                    'file_size': transcript_file.stat().st_size,
                    'created_at': datetime.fromtimestamp(transcript_file.stat().st_ctime).isoformat()
                })
                
            except Exception as e:
                logger.warning(f"Error reading transcript file {transcript_file}: {str(e)}")
        
        return jsonify({
            'session_id': session_id,
            'transcripts': transcripts,
            'total_transcripts': len(transcripts)
        })
        
    except Exception as e:
        logger.error(f"Error getting session transcripts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/course/<session_id>/slides', methods=['GET'])
def get_course_slide_images(session_id):
    """Get slide images for a course by converting PowerPoint to images"""
    try:
        # Check if course exists using file_manager
        course_data = file_manager.load_course_session(session_id)
        if not course_data:
            return jsonify({'error': 'Course not found'}), 404
        
        presentation_file = course_data.get('presentation_file', '')
        if not presentation_file:
            return jsonify({'error': 'No presentation file found'}), 404
        
        # Convert presentation file path to proper format
        pptx_path = Path(presentation_file.replace('\\', '/'))
        if not pptx_path.exists():
            return jsonify({'error': 'Presentation file not found'}), 404
        
        # Convert PowerPoint to images
        slide_images = _convert_pptx_to_images(pptx_path, session_id)
        
        return jsonify({
            'session_id': session_id,
            'slide_images': slide_images,
            'total_slides': len(slide_images)
        })
        
    except Exception as e:
        logger.error(f"Error getting course slide images: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/images/<path:image_path>', methods=['GET'])
def serve_slide_image(image_path):
    """Serve slide images"""
    try:
        # Decode and normalize the image path
        decoded_path = urllib.parse.unquote(image_path)
        normalized_path = decoded_path.replace('\\', '/')
        
        # Construct full path
        if normalized_path.startswith('data/'):
            full_path = Path(normalized_path)
        else:
            full_path = Path('data') / normalized_path
        
        # Security check - ensure file is in data directory
        if not str(full_path).replace('\\', '/').startswith('data/'):
            return jsonify({'error': 'Invalid image path'}), 403
        
        if not full_path.exists():
            logger.error(f"Image file not found: {full_path}")
            return jsonify({'error': 'Image not found'}), 404
        
        logger.info(f"Serving image: {full_path}")
        return send_file(full_path, mimetype='image/png')
        
    except Exception as e:
        logger.error(f"Error serving image: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Audio endpoints
@app.route('/api/audio/voices', methods=['GET'])
def get_voices():
    """Get available TTS voices"""
    try:
        voices = audio_manager.get_available_voices()
        return jsonify(voices)
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/generate', methods=['POST'])
def generate_audio():
    """Generate audio for slide content"""
    try:
        data = request.json
        slide_data = data.get('slideData', {})
        options = data.get('options', {})
        
        if not slide_data:
            return jsonify({'error': 'No slide data provided'}), 400
        
        # Extract session info if available for proper file organization
        session_id = request.json.get('session_id', None)
        slide_number = slide_data.get('slide_number', None)
        audio_file = audio_manager.generate_slide_audio(slide_data, options, session_id, slide_number)
        return send_file(audio_file, mimetype='audio/wav')
        
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/transcribe', methods=['POST'])
def transcribe_audio_v2():
    """Transcribe audio to text (v2 endpoint)"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        transcription = audio_manager.transcribe_audio(audio_file)
        
        return jsonify({'transcription': transcription})
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/file/<path:filename>', methods=['GET'])
def serve_audio_file(filename):
    """Serve audio files for playback"""
    try:
        # Decode the filename
        decoded_filename = urllib.parse.unquote(filename)
        
        # Normalize path separators (handle both Windows and Unix paths)
        normalized_path = decoded_filename.replace('\\', '/')
        audio_path = Path(normalized_path)
        
        # Security check - ensure file is in data directory (more flexible for session-based structure)
        audio_path_str = str(audio_path).replace('\\', '/')
        if not audio_path_str.startswith('data/'):
            return jsonify({'error': 'Invalid file path'}), 403
        
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return jsonify({'error': 'Audio file not found'}), 404
        
        logger.info(f"Serving audio file: {audio_path}")
        return send_file(audio_path, mimetype='audio/wav')
        
    except Exception as e:
        logger.error(f"Error serving audio file: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Conversation endpoints
@app.route('/api/conversation/start', methods=['POST'])
def start_conversation():
    """Start a conversation session"""
    try:
        data = request.json
        session_id = data.get('sessionId', '')
        slide_context = data.get('slideContext', {})
        
        conversation_session_id = conversation_manager.start_conversation(session_id, slide_context)
        return jsonify({'conversation_session_id': conversation_session_id})
        
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/<session_id>/history', methods=['GET'])
def get_conversation_history(session_id):
    """Get conversation history for a session"""
    try:
        history = conversation_manager.get_conversation_history(session_id)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/<session_id>/end', methods=['POST'])
def end_conversation(session_id):
    """End a conversation session"""
    try:
        conversation_manager.end_conversation(session_id)
        return jsonify({'message': 'Conversation ended successfully'})
    except Exception as e:
        logger.error(f"Error ending conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

# File management endpoints
@app.route('/api/files/stats', methods=['GET'])
def get_file_stats():
    """Get storage statistics"""
    try:
        stats = file_manager.get_storage_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting file stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/cleanup', methods=['POST'])
def cleanup_files():
    """Cleanup old files"""
    try:
        data = request.json
        max_age = data.get('maxAge', 30)
        
        result = file_manager.cleanup_old_files(max_age)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error cleaning up files: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/info', methods=['GET'])
def get_file_info():
    """Get file information"""
    try:
        file_path = request.args.get('path', '')
        if not file_path:
            return jsonify({'error': 'No file path provided'}), 400
        
        file_info = file_manager.get_file_info(file_path)
        return jsonify(file_info)
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload a file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        result = file_manager.upload_file(file)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/import-course', methods=['POST'])
def import_course():
    """Import a course from file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        result = file_manager.import_course(file)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error importing course: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Global error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all uncaught exceptions"""
    logger.error(f"Uncaught exception: {str(e)}", exc_info=True)
    return jsonify({'error': 'An unexpected error occurred'}), 500

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_info = {
        'sid': request.sid,
        'remote_addr': request.environ.get('REMOTE_ADDR', 'unknown'),
        'user_agent': request.environ.get('HTTP_USER_AGENT', 'unknown'),
        'timestamp': datetime.now().isoformat()
    }
    logger.info(f"[WebSocket] Client connected: {client_info}")
    
    # Send initial connection confirmation with server info
    emit('connected', {
        'message': 'Connected to AI Teacher server',
        'server_time': datetime.now().isoformat(),
        'session_id': request.sid,
        'connection_id': request.sid
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    disconnect_info = {
        'sid': request.sid,
        'timestamp': datetime.now().isoformat()
    }
    logger.info(f"[WebSocket] Client disconnected: {disconnect_info}")

@socketio.on('join_session')
def handle_join_session(data):
    """Handle client joining a generation session"""
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)
        logger.info(f"[WebSocket] Client {request.sid} joined session {session_id}")
        
        # Send confirmation and current session status if available
        session_status = active_sessions.get(session_id, {})
        emit('session_joined', {
            'session_id': session_id,
            'status': session_status.get('status', 'unknown'),
            'progress': session_status.get('progress', 0),
            'timestamp': datetime.now().isoformat()
        })
        
        # Send immediate heartbeat to confirm connection
        _send_heartbeat(session_id)
    else:
        logger.warning(f"[WebSocket] Client {request.sid} attempted to join session without session_id")
        emit('error', {'message': 'No session_id provided'})

def _generate_course_async(session_id, data):
    """Asynchronously generate a complete course presentation"""
    try:
        # Get progress tracker
        tracker = progress_trackers.get(session_id)
        if tracker:
            # Add progress callback for real-time updates
            tracker.add_progress_callback(lambda status: _emit_enhanced_progress(session_id, status))
        
        # Send initial heartbeat and start heartbeat thread
        _send_heartbeat(session_id)
        heartbeat_thread = _start_heartbeat_thread(session_id)
        logger.info(f"Started heartbeat monitoring for session {session_id}")
        
        # Stage 1: Generate course structure
        if tracker:
            tracker.start_stage('course_structure', {
                'topic': data['topic'],
                'complexity': data['complexity'],
                'duration': data['duration']
            })
        
        _update_session_progress(session_id, 10, 'Generating course structure', {
            'stage': 'course_structure',
            'details': 'Analyzing topic and creating hierarchical course outline'
        })
        
        # Handle flexible field naming
        learning_style = data.get('learning_style') or data.get('learningStyle')
        
        course_structure = course_generator.generate_structure(
            topic=data['topic'],
            complexity=data['complexity'],
            duration=data['duration'],
            learning_style=learning_style,
            customizations={**data.get('customizations', {}), 'session_id': session_id}
        )
        
        # Update tracker with course structure stats
        if tracker:
            main_topics = course_structure.get('main_topics', [])
            subtopics_count = sum(len(topic.get('subtopics', [])) for topic in main_topics)
            tracker.update_statistics(
                total_topics=len(main_topics),
                total_subtopics=subtopics_count
            )
            tracker.complete_stage('course_structure')
        
        # Send heartbeat and detailed progress
        _send_heartbeat(session_id)
        _update_session_progress(session_id, 20, 'Course structure completed', {
            'stage': 'course_structure_complete',
            'details': f"Generated {len(course_structure.get('main_topics', []))} main topics",
            'topics_count': len(course_structure.get('main_topics', [])),
            'estimated_slides': 'calculating...'
        })
        
        # Stage 2: Plan presentation
        if tracker:
            tracker.start_stage('presentation_planning')
            
        _update_session_progress(session_id, 25, 'Planning presentation format', {
            'stage': 'presentation_planning',
            'details': 'Converting course structure to sequential slide format'
        })
        
        # Handle flexible field naming
        slide_count = data.get('slide_count') or data.get('slideCount', 'auto')
        content_density = data.get('content_density') or data.get('contentDensity', 'medium')
        
        presentation_plan = presentation_planner.create_plan(
            course_structure,
            slide_count,
            content_density
        )
        
        # Add session_id to presentation plan for logging in slide generator
        presentation_plan['session_id'] = session_id

        # Update tracker with slide planning stats
        total_slides = len(presentation_plan.get('slides', []))
        if tracker:
            tracker.update_statistics(total_slides=total_slides)
            tracker.complete_stage('presentation_planning')
        
        # Send heartbeat and update with slide count
        _send_heartbeat(session_id)
        _update_session_progress(session_id, 35, 'Presentation plan completed', {
            'stage': 'presentation_planning_complete',
            'details': f"Planned {total_slides} slides for presentation",
            'total_slides': total_slides,
            'estimated_duration': presentation_plan.get('estimated_duration', 'Unknown')
        })
        
        # Stage 3: Generate slide content
        if tracker:
            tracker.start_stage('slide_generation', {
                'total_slides': total_slides,
                'batch_size': data.get('batch_size', 5)
            })
            
        _update_session_progress(session_id, 40, 'Generating slide content', {
            'stage': 'slide_generation',
            'details': f'Creating detailed content for {total_slides} slides',
            'current_slide': 0,
            'total_slides': total_slides
        })
        
        # Handle flexible field naming
        batch_size = data.get('batch_size') or data.get('batchSize', 5)
        
        slides_content = slide_generator.generate_all_slides(
            presentation_plan,
            batch_size=batch_size,
            progress_callback=lambda p: _update_slide_generation_progress(
                session_id, p, total_slides, tracker
            )
        )
        
        # Add session_id to each slide for logging in image manager
        for slide in slides_content:
            slide['session_id'] = session_id
            
        # Complete slide generation stage
        if tracker:
            tracker.complete_stage('slide_generation')
        
        # Stage 4: Process images
        total_images = sum(len(slide.get('images', [])) for slide in slides_content)
        if tracker:
            tracker.start_stage('image_processing', {'total_images': total_images})
            tracker.update_statistics(total_images=total_images)
            
        _send_heartbeat(session_id)
        _update_session_progress(session_id, 70, 'Processing images', {
            'stage': 'image_processing',
            'details': f'Finding and generating {total_images} images for slides',
            'current_image': 0,
            'total_images': total_images
        })
        
        processed_slides = image_manager.process_all_images(
            slides_content,
            progress_callback=lambda p: _update_image_progress(
                session_id, p, total_images, tracker
            )
        )
        
        # Complete image processing stage
        if tracker:
            tracker.complete_stage('image_processing')
        
        # Stage 5: Build presentation
        if tracker:
            tracker.start_stage('presentation_building')
            
        _send_heartbeat(session_id)
        _update_session_progress(session_id, 85, 'Building presentation', {
            'stage': 'presentation_building',
            'details': 'Creating PowerPoint file with slides and images'
        })
        
        presentation_file = presentation_builder.build_presentation(
            processed_slides,
            data['topic'],
            session_id=session_id,
            theme=data.get('theme', 'default')
        )
        
        # Complete presentation building stage
        if tracker:
            tracker.complete_stage('presentation_building')
        
        # Stage 6: Generate audio
        if tracker:
            tracker.start_stage('audio_generation', {'total_audio_files': total_slides})
            tracker.update_statistics(total_audio_files=total_slides)
            
        _send_heartbeat(session_id)
        _update_session_progress(session_id, 95, 'Generating audio narration', {
            'stage': 'audio_generation',
            'details': f'Creating TTS audio for {total_slides} slides',
            'current_audio': 0,
            'total_audio': total_slides
        })
        
        # Debug: Log slide transcripts before audio generation
        logger.info(f"Generating audio for {len(processed_slides)} slides")
        for i, slide in enumerate(processed_slides):
            transcript = slide.get('transcript', '')
            logger.debug(f"Slide {i+1} transcript length: {len(transcript)} chars")
            if not transcript:
                logger.warning(f"Slide {i+1} has no transcript!")
        
        # Debug: Log TTS settings
        tts_voice = data.get('voice', 'default')  # Fixed: use 'voice' not 'tts_voice'
        tts_speed = data.get('speed', 1.0)  # Fixed: use 'speed' not 'tts_speed'
        logger.info(f"TTS Settings - Voice: '{str(tts_voice)[:50]}...', Speed: {tts_speed}")
        
        audio_files = audio_manager.synthesize_all_speech(
            slides_content=processed_slides,
            voice=tts_voice,
            speed=tts_speed,
            session_id=session_id,
            progress_callback=lambda p: _update_audio_generation_progress(
                session_id, p, total_slides, tracker
            )
        )
        
        # Debug: Log audio generation results
        successful_audio = len([f for f in audio_files if f])
        logger.info(f"Audio generation results: {successful_audio}/{len(audio_files)} files generated successfully")
        for i, audio_file in enumerate(audio_files):
            if audio_file:
                logger.debug(f"Slide {i+1} audio: {audio_file}")
            else:
                logger.warning(f"Slide {i+1} audio generation failed!")
        
        # Complete audio generation stage
        if tracker:
            tracker.complete_stage('audio_generation')
            tracker.update_statistics(audio_files_generated=len([f for f in audio_files if f]))
        
        # Stage 7: Save the final presentation and course data
        if tracker:
            tracker.start_stage('saving_presentation', {
                'presentation_file': presentation_file,
                'audio_files_count': len([f for f in audio_files if f])
            })
        
        _emit_enhanced_progress(session_id, tracker.update_stage("saving_presentation", "Finalizing and saving all course assets.") if tracker else {})
        
        final_course_data = file_manager.save_presentation(
            presentation_file=presentation_file,
            audio_files=audio_files,
            course_structure=course_structure,
            presentation_plan=presentation_plan,
            slides_content=slides_content,  # Pass the generated slide content
            original_data=data
        )
        
        if tracker:
            tracker.add_log_entry("info", f"Final course data saved for session: {session_id}")
            tracker.complete_stage('saving_presentation')
        
        _emit_enhanced_progress(session_id, tracker.get_current_status() if tracker else {})
        
        # Automatically generate slide images for immediate presentation viewing
        logger.info(f"Generating slide images for session {session_id}")
        try:
            slide_images = _convert_pptx_to_images(Path(presentation_file), session_id)
            logger.info(f"Successfully generated {len(slide_images)} slide images for immediate viewing")
        except Exception as e:
            logger.warning(f"Failed to generate slide images during course completion: {str(e)}")
            # Don't fail the entire course generation if image conversion fails
        
        # Update session with completion
        active_sessions[session_id].update({
            'status': 'completed',
            'progress': 100,
            'stage': 'Presentation ready',
            'result': final_course_data,
            'end_time': time.time()
        })
        
        # Send final heartbeat and completion event with detailed data
        _send_heartbeat(session_id)
        logger.info(f"Course generation completed for session {session_id}")
        
        # Get final progress report from tracker
        progress_report = {}
        if tracker:
            progress_report = tracker.export_progress_report()
        
        # Emit completion event with comprehensive data
        socketio.emit('course_complete', {
            'session_id': session_id,
            'course_data': final_course_data,
            'summary': {
                'total_slides': total_slides,
                'total_images': total_images,
                'generation_time': time.time() - active_sessions[session_id]['start_time'],
                'presentation_file': presentation_file,
                'audio_files_count': len([f for f in audio_files if f]),
                'transcript_files_count': len(final_course_data.get('transcript_files', []))
            },
            'progress_report': progress_report
        }, room=session_id)
        
        logger.info(f"Emitted course_complete event for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error in course generation: {str(e)}")
        active_sessions[session_id].update({
            'status': 'error',
            'stage': 'Generation failed',
            'error': str(e),
            'end_time': time.time()
        })
        
        # Send heartbeat and emit detailed error event
        _send_heartbeat(session_id)
        socketio.emit('course_error', {
            'session_id': session_id,
            'error': str(e),
            'stage': active_sessions[session_id].get('stage', 'Unknown'),
            'timestamp': time.time()
        }, room=session_id)
        
        logger.error(f"Emitted course_error event for session {session_id}")

def _update_session_progress(session_id, progress, stage, details=None):
    """Update the progress of a generation session and emit to client."""
    if session_id in active_sessions:
        now = time.time()
        session = active_sessions[session_id]
        session['progress'] = progress
        session['stage'] = stage
        session['details'] = details
        session['last_updated'] = now
        
        # logger.info(f"Progress update for {session_id}: {progress}% - {stage}")
        
        # Calculate statistics for the simple progress event
        elapsed_time = now - session['start_time']
        if elapsed_time > 0:
            progress_per_second = progress / elapsed_time
            estimated_total_time = progress / progress_per_second
            estimated_remaining_time = estimated_total_time - elapsed_time
            estimated_remaining_percentage = (estimated_remaining_time / estimated_total_time) * 100 if estimated_total_time > 0 else 100
        else:
            progress_per_second = 0
            estimated_total_time = 0
            estimated_remaining_time = 0
            estimated_remaining_percentage = 0
        
        # Emit detailed progress update
        progress_data = {
            'session_id': session_id,
            'progress': progress,
            'step': stage,
            'timestamp': now,
            'estimated_total_time': round(estimated_total_time, 3),
            'estimated_remaining_time': round(estimated_remaining_time, 3),
            'estimated_remaining_percentage': round(estimated_remaining_percentage, 2),
            'progress_per_second': round(progress_per_second, 3)
        }
        
        if details:
            progress_data.update(details)
            
        socketio.emit('course_progress', progress_data, room=session_id)
        logger.info(f"Progress update for {session_id}: {progress}% - {stage}")

def _send_heartbeat(session_id):
    """Send heartbeat to keep WebSocket connection alive"""
    heartbeat_data = {
        'session_id': session_id,
        'timestamp': time.time(),
        'status': 'alive',
        'server_time': datetime.now().isoformat()
    }
    
    logger.debug(f"Sending heartbeat to session {session_id} at {heartbeat_data['server_time']}")
    socketio.emit('heartbeat', heartbeat_data, room=session_id)

def _start_heartbeat_thread(session_id):
    """Start a background thread to send periodic heartbeats"""
    def heartbeat_worker():
        logger.info(f"Starting heartbeat thread for session {session_id}")
        while session_id in active_sessions:
            session = active_sessions.get(session_id)
            if not session or session.get('status') == 'completed' or session.get('status') == 'failed':
                logger.info(f"Stopping heartbeat thread for session {session_id} - status: {session.get('status') if session else 'session removed'}")
                break
            
            try:
                _send_heartbeat(session_id)
                time.sleep(10)  # Send heartbeat every 10 seconds
            except Exception as e:
                logger.error(f"Error in heartbeat thread for session {session_id}: {str(e)}")
                break
        
        logger.info(f"Heartbeat thread ended for session {session_id}")
    
    # Start the heartbeat thread
    heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
    heartbeat_thread.start()
    return heartbeat_thread

def _emit_enhanced_progress(session_id, status):
    """Emit enhanced progress updates with detailed information"""
    try:
        # Emit the enhanced progress data
        socketio.emit('enhanced_progress', status, room=session_id)
        
        # Also emit the legacy format for backward compatibility
        socketio.emit('course_progress', {
            'session_id': session_id,
            'progress': status['overall_progress'],
            'step': status['current_stage']['name'],
            'stage': status['current_stage']['id'],
            'details': status['current_stage']['description'],
            'timestamp': time.time(),
            'statistics': status['statistics'],
            'timing': status['timing']
        }, room=session_id)
        
    except Exception as e:
        logger.error(f"Error emitting enhanced progress: {str(e)}")
    
def _update_slide_generation_progress(session_id, progress_percent, total_slides, tracker=None):
    """Update progress for slide generation with detailed info"""
    current_slide = int((progress_percent / 100) * total_slides)
    base_progress = 40  # Starting progress for slide generation
    adjusted_progress = base_progress + (progress_percent * 0.3)  # 30% of total for slides
    
    # Update enhanced tracker
    if tracker:
        tracker.update_statistics(slides_generated=current_slide)
        tracker.update_stage_progress('slide_generation', progress=progress_percent, details={
            'current_slide': current_slide,
            'total_slides': total_slides,
            'progress_percent': progress_percent
        })
    
    _update_session_progress(session_id, adjusted_progress, 'Generating slide content', {
        'stage': 'slide_generation',
        'details': f'Generated {current_slide} of {total_slides} slides',
        'current_slide': current_slide,
        'total_slides': total_slides,
        'slide_progress': progress_percent
    })
    
    # Send heartbeat every few slides
    if current_slide % 5 == 0:
        _send_heartbeat(session_id)

def _update_image_progress(session_id, progress_percent, total_images, tracker=None):
    """Update progress for image processing with detailed info"""
    current_image = int((progress_percent / 100) * total_images)
    base_progress = 70  # Starting progress for image processing
    adjusted_progress = base_progress + (progress_percent * 0.15)  # 15% of total for images
    
    # Update enhanced tracker
    if tracker:
        tracker.update_statistics(images_processed=current_image)
        tracker.update_stage_progress('image_processing', progress=progress_percent, details={
            'current_image': current_image,
            'total_images': total_images,
            'progress_percent': progress_percent
        })
    
    _update_session_progress(session_id, adjusted_progress, 'Processing images', {
        'stage': 'image_processing',
        'details': f'Processed {current_image} of {total_images} images',
        'current_image': current_image,
        'total_images': total_images,
        'image_progress': progress_percent
    })
    
    # Send heartbeat every few images
    if current_image % 10 == 0:
        _send_heartbeat(session_id)

def _update_audio_generation_progress(session_id, progress_percent, total_slides, tracker=None):
    """Update progress for audio generation."""
    current_slide = int((progress_percent / 100) * total_slides)
    base_progress = 85  # Starting progress for audio generation
    adjusted_progress = base_progress + (progress_percent * 0.10)  # 10% of total for audio

    if tracker:
        tracker.update_statistics(audio_files_generated=current_slide)
        tracker.update_stage_progress('audio_generation', progress=progress_percent, details={
            'current_audio': current_slide,
            'total_audio': total_slides,
        })

    _update_session_progress(session_id, adjusted_progress, 'Generating audio narration', {
        'stage': 'audio_generation',
        'details': f'Generated audio for {current_slide} of {total_slides} slides',
        'current_audio': current_slide,
        'total_audio': total_slides,
    })

def _transform_course_data_for_frontend(course_data):
    """Transform course data from storage format to frontend format"""
    try:
        # Extract slides content
        slides_content = course_data.get('slides_content', [])
        
        # Transform each slide to include transcript and proper format
        transformed_slides = []
        for slide in slides_content:
            # Use original transcript if available, otherwise generate from slide content
            transcript = slide.get('transcript', '') or _generate_transcript_from_slide(slide)
            
            transformed_slide = {
                'title': slide.get('title', ''),
                'content': slide.get('main_points', []),
                'transcript': transcript,
                'slide_number': slide.get('slide_number', 0),
                'slide_type': slide.get('slide_type', 'content'),
                'estimated_time': slide.get('estimated_time', 1.0),
                'images': []  # TODO: Extract image data if available
            }
            transformed_slides.append(transformed_slide)
        
        # Normalize audio file paths (convert Windows paths to Unix-style for URL compatibility)
        audio_files = course_data.get('audio_files', [])
        normalized_audio_files = [path.replace('\\', '/') for path in audio_files]
        
        # Build the response in the format expected by frontend
        result = {
            'session_id': course_data.get('session_id', ''),
            'course_title': course_data.get('course_title', 'Untitled Course'),
            'topic': course_data.get('topic', ''),
            'complexity': course_data.get('complexity', 'intermediate'),
            'duration': course_data.get('duration', ''),
            'slides_content': transformed_slides,
            'audio_files': normalized_audio_files,
            'presentation_file': course_data.get('presentation_file', ''),
            'metadata': course_data.get('metadata', {}),
            'status': 'completed'
        }
        
        logger.info(f"Transformed course data for session {result['session_id']}: {len(transformed_slides)} slides, {len(normalized_audio_files)} audio files")
        
        return result
        
    except Exception as e:
        logger.error(f"Error transforming course data: {str(e)}")
        return course_data  # Return original data if transformation fails

def _generate_transcript_from_slide(slide):
    """Generate a transcript from slide content for TTS"""
    try:
        transcript_parts = []
        
        # Check if transcript already exists
        if slide.get('transcript'):
            return slide['transcript']
        
        # Primary transcript source: content_brief (this is the main narrative)
        content_brief = slide.get('content_brief', '')
        if content_brief:
            transcript_parts.append(content_brief)
        
        # Add main points as additional context if needed
        main_points = slide.get('main_points', [])
        if main_points and not content_brief:
            # Only use main points if no content_brief is available
            for point in main_points:
                if isinstance(point, str):
                    # Clean up bullet points and formatting
                    cleaned_point = point.replace('  - ', '').replace('- ', '').strip()
                    if cleaned_point and not cleaned_point.startswith('Example:'):
                        transcript_parts.append(cleaned_point)
        
        # Fallback: Use slide title and basic content
        if not transcript_parts:
            title = slide.get('title', '')
            if title:
                transcript_parts.append(f"This slide covers {title}.")
            
            # Try to extract any text content
            content = slide.get('content', slide.get('bullet_points', []))
            if isinstance(content, list) and content:
                first_few_points = content[:3]  # Don't overwhelm with too many points
                for point in first_few_points:
                    if isinstance(point, str) and len(point.strip()) > 0:
                        cleaned_point = point.replace('•', '').replace('-', '').strip()
                        transcript_parts.append(cleaned_point)
        
        # Add transition note for natural flow
        transition_note = slide.get('transition_note', '')
        if transition_note and transition_note != "End of presentation.":
            transcript_parts.append(transition_note)
        
        # Join all parts with natural pauses
        transcript = ' '.join(transcript_parts)
        
        # Clean up the transcript for TTS
        transcript = transcript.replace('..', '.').replace('  ', ' ').strip()
        
        # Fallback if no transcript generated
        if not transcript:
            title = slide.get('title', '')
            if title:
                transcript = f"This slide is titled: {title}"
            else:
                transcript = "This slide contains visual content."
        
        return transcript
        
    except Exception as e:
        logger.error(f"Error generating transcript: {str(e)}")
        return slide.get('content_brief', slide.get('title', 'Content not available'))

def _convert_pptx_to_images(pptx_path, session_id):
    """Convert PowerPoint presentation to individual slide images"""
    try:
        # Use session-based image directory for slide images
        subdirs = file_manager.get_session_subdirs(session_id)
        output_dir = subdirs['images'] / 'slide_images'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if images already exist
        existing_images = list(output_dir.glob("slide_*.png"))
        if existing_images:
            logger.info(f"Found {len(existing_images)} existing slide images")
            slide_images = []
            
            # Sort by slide number, not alphabetically
            def get_slide_number(path):
                try:
                    return int(path.stem.split('_')[1])
                except:
                    return 0
            
            for img_path in sorted(existing_images, key=get_slide_number):
                slide_num = int(img_path.stem.split('_')[1])
                normalized_path = str(img_path).replace('\\', '/')
                slide_images.append({
                    'slide_number': slide_num,
                    'image_path': normalized_path,
                    'image_url': f"/api/images/{normalized_path}"
                })
            return slide_images
        
        # Method 1: Try using LibreOffice (best quality)
        slide_images = _convert_pptx_with_libreoffice(pptx_path, output_dir)
        if slide_images:
            logger.info(f"Successfully converted {len(slide_images)} slides using LibreOffice")
            return slide_images
        
        # Method 2: Try using python-pptx to PDF then PDF to images
        slide_images = _convert_pptx_via_pdf(pptx_path, output_dir)
        if slide_images:
            logger.info(f"Successfully converted {len(slide_images)} slides via PDF")
            return slide_images
        
        # Method 3: Try using COM automation (Windows only)
        if os.name == 'nt':
            slide_images = _convert_pptx_with_com(pptx_path, output_dir)
            if slide_images:
                logger.info(f"Successfully converted {len(slide_images)} slides using COM")
                return slide_images
        
        # Fallback: Use existing processed images from data/images/processed/
        processed_dir = Path("data/images/processed")
        if processed_dir.exists():
            slide_images = []
            processed_images = list(processed_dir.glob("slide_*.png"))
            
            # Group images by slide number and only take the first image per slide
            slide_groups = {}
            for img_path in processed_images:
                try:
                    slide_num = int(img_path.stem.split('_')[1])
                    if slide_num not in slide_groups:
                        slide_groups[slide_num] = img_path
                except:
                    continue
            
            # Sort by slide number and create slide_images list
            for slide_num in sorted(slide_groups.keys()):
                img_path = slide_groups[slide_num]
                normalized_path = str(img_path).replace('\\', '/')
                slide_images.append({
                    'slide_number': slide_num,
                    'image_path': normalized_path,
                    'image_url': f"/api/images/{normalized_path}"
                })
            
            if slide_images:
                logger.info(f"Using {len(slide_images)} existing processed images (grouped by slide)")
                return slide_images
        
        # If all else fails, return empty list
        logger.warning("No slide images could be generated or found")
        return []
        
    except Exception as e:
        logger.error(f"Error converting PowerPoint to images: {str(e)}")
        return []

def _convert_pptx_with_libreoffice(pptx_path, output_dir):
    """Convert PowerPoint to images using LibreOffice"""
    try:
        import subprocess
        
        # Try to convert PPTX to PDF first using LibreOffice
        pdf_path = output_dir / "temp_presentation.pdf"
        
        # LibreOffice command to convert PPTX to PDF
        cmd = [
            'soffice', '--headless', '--convert-to', 'pdf',
            '--outdir', str(output_dir), str(pptx_path)
        ]
        
        logger.info(f"Running LibreOffice conversion: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.warning(f"LibreOffice conversion failed: {result.stderr}")
            return []
        
        # Find the generated PDF
        pdf_files = list(output_dir.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF file generated by LibreOffice")
            return []
        
        pdf_path = pdf_files[0]
        
        # Convert PDF to images
        slide_images = _convert_pdf_to_images(pdf_path, output_dir)
        
        # Clean up PDF
        try:
            pdf_path.unlink()
        except:
            pass
        
        return slide_images
        
    except Exception as e:
        logger.error(f"LibreOffice conversion failed: {str(e)}")
        return []

def _convert_pptx_via_pdf(pptx_path, output_dir):
    """Convert PowerPoint to PDF then to images"""
    try:
        # Try using pdf2image if available
        try:
            from pdf2image import convert_from_path
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("pdf2image or PyMuPDF not available")
            return []
        
        # First try to convert PPTX to PDF using python-pptx export (if available)
        # This is a placeholder - python-pptx doesn't have direct PDF export
        # We'll use PyMuPDF to work with any existing PDF
        
        # For now, skip this method if we don't have the tools
        return []
        
    except Exception as e:
        logger.error(f"PDF conversion failed: {str(e)}")
        return []

def _convert_pptx_with_com(pptx_path, output_dir):
    """Convert PowerPoint to images using COM automation (Windows only).
    This implementation exports slides one-by-one which is slower but avoids the
    directory-creation race that Presentation.Export sometimes triggers.
    """
    try:
        import win32com.client
        from win32com.client import constants

        # Launch PowerPoint (needs to be visible, window can stay in background)
        pp = win32com.client.Dispatch("PowerPoint.Application")
        pp.Visible = True

        try:
            # Open the presentation read-only, no window popup
            pres = pp.Presentations.Open(str(pptx_path.absolute()), ReadOnly=1)

            # Ensure the export directory exists and is empty
            output_dir.mkdir(parents=True, exist_ok=True)
            for f in output_dir.glob("*.png"):
                try:
                    f.unlink()
                except Exception:
                    pass

            # Use absolute paths for PowerPoint COM
            abs_output_dir = output_dir.resolve()
            
            slide_images: list[dict] = []
            width, height = 1920, 1080

            # Export every slide individually
            for i in range(1, pres.Slides.Count + 1):
                slide = pres.Slides(i)
                img_path = abs_output_dir / f"slide_{i}.png"
                slide.Export(str(img_path), "PNG", width, height)

                # Convert absolute path back to relative path for URL serving
                relative_path = img_path.relative_to(Path.cwd())
                normalized_path = str(relative_path).replace("\\", "/")
                slide_images.append({
                    "slide_number": i,
                    "image_path": normalized_path,
                    "image_url": f"/api/images/{normalized_path}",
                })

            if not slide_images:
                logger.warning("COM export produced no images")
                return []

            logger.info(f"Exported {len(slide_images)} slides via COM automation (per-slide)")
            return slide_images

        finally:
            # Clean up PowerPoint COM objects
            try:
                pres.Close()
            except Exception:
                pass
            try:
                pp.Quit()
            except Exception:
                pass

    except Exception as e:
        logger.error(f"COM automation failed: {str(e)}")
        return []

def _convert_pdf_to_images(pdf_path, output_dir):
    """Convert PDF to individual slide images"""
    try:
        from pdf2image import convert_from_path
        
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300, fmt='PNG')
        
        slide_images = []
        
        for i, image in enumerate(images, 1):
            img_path = output_dir / f"slide_{i}.png"
            image.save(img_path, 'PNG')
            
            normalized_path = str(img_path).replace('\\', '/')
            slide_images.append({
                'slide_number': i,
                'image_path': normalized_path,
                'image_url': f"/api/images/{normalized_path}"
            })
        
        return slide_images
        
    except Exception as e:
        logger.error(f"PDF to images conversion failed: {str(e)}")
        return []

# Request handlers to prevent response errors
@app.before_request
def before_request():
    """Handle before request processing"""
    try:
        # Ensure request context is properly set
        # Let Flask-CORS handle all CORS requests including OPTIONS
        pass
    except Exception as e:
        logger.error(f"Error in before_request: {str(e)}")
        # Return a proper response instead of None
        response = make_response(jsonify({'error': 'Request processing error'}), 500)
        return response

@app.after_request
def after_request(response):
    """Handle after request processing"""
    try:
        # Ensure the response has proper status and headers
        if not hasattr(response, 'status_code'):
            response.status_code = 200
        
        # Don't add CORS headers here since Flask-CORS handles them
        # Just ensure the response is properly formatted
        return response
    except Exception as e:
        logger.error(f"Error in after_request: {str(e)}")
        # Return the original response even if there's an error
        return response

if __name__ == '__main__':
    # Note: FileManager now handles directory creation with session-based structure
    # The old flat directory structure is no longer created by default
    # FileManager creates: data/sessions, data/exports, data/temp
    
    # Run the application
    logger.info("Starting AI-Powered Educational Presentation System")
    logger.info("Using session-based data organization structure")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)