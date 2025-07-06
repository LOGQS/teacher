#!/usr/bin/env python3
"""
Audio Manager - TTS and STT functionality
Handles text-to-speech synthesis and speech-to-text transcription.
"""

import os
import logging
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import pyttsx3
from groq import Groq

logger = logging.getLogger(__name__)

class AudioManager:
    """Manages audio synthesis and transcription"""
    
    def __init__(self, file_manager=None):
        """Initialize the audio manager"""
        self.file_manager = file_manager
        self.tts_engine = None
        self.last_tts_error = None
        self.tts_completed = False
        
        # Initialize TTS engine
        try:
            logger.info("Initializing TTS engine...")
            self.tts_engine = pyttsx3.init()
            self._setup_tts_callbacks()
            logger.info("TTS engine initialized successfully")
            self._configure_tts_engine()
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {str(e)}")
            import traceback
            logger.error(f"TTS initialization traceback: {traceback.format_exc()}")
        
        # Initialize Groq client for STT
        groq_api_key = os.environ.get('GROQ_API_KEY')
        if groq_api_key:
            self.groq_client = Groq(api_key=groq_api_key)
        else:
            logger.warning("GROQ_API_KEY not found - STT will be disabled")
            self.groq_client = None
        
        # Audio directories will be created per session via file_manager
        
        # Available voices
        self.available_voices = self._get_available_voices()
    
    def _get_audio_dir(self, session_id: str) -> Path:
        """Get audio directory for a specific session"""
        if self.file_manager:
            subdirs = self.file_manager.get_session_subdirs(session_id)
            return subdirs['audio']
        else:
            # Fallback to old structure if no file_manager
            audio_dir = Path('data/audio')
            audio_dir.mkdir(parents=True, exist_ok=True)
            return audio_dir
    
    def _setup_tts_callbacks(self):
        """Set up callbacks for TTS events to improve error handling."""
        if not self.tts_engine:
            return

        def on_end(name, completed):
            logger.info(f"TTS utterance finished. Name: {name}, Completed: {completed}")
            self.tts_completed = completed
            if not completed:
                self.last_tts_error = f"TTS engine failed to complete utterance '{name}'."

        self.tts_engine.connect('finished-utterance', on_end)
    
    def _configure_tts_engine(self):
        """Configure TTS engine with default settings"""
        try:
            if self.tts_engine:
                # Set default rate and volume
                self.tts_engine.setProperty('rate', 200)  # Words per minute
                self.tts_engine.setProperty('volume', 0.8)  # Volume level (0-1)
                
                # Log current TTS engine properties
                logger.info(f"TTS Engine configured successfully")
                logger.info(f"Current rate: {self.tts_engine.getProperty('rate')}")
                logger.info(f"Current volume: {self.tts_engine.getProperty('volume')}")
                
                # Test basic TTS functionality
                self._test_tts_basic()
                
        except Exception as e:
            logger.warning(f"Error configuring TTS engine: {str(e)}")
            import traceback
            logger.warning(f"TTS configuration traceback: {traceback.format_exc()}")
    
    def _test_tts_basic(self):
        """Test basic TTS functionality"""
        try:
            # Create a simple test file
            test_dir = Path('data/test_audio')
            test_dir.mkdir(parents=True, exist_ok=True)
            test_file = test_dir / 'test.wav'
            
            # Try to generate a simple test audio
            self.tts_engine.save_to_file("Test audio generation", str(test_file))
            self.tts_engine.runAndWait()
            
            if test_file.exists():
                file_size = test_file.stat().st_size
                logger.info(f"TTS basic test successful: {test_file} (size: {file_size} bytes)")
                # Clean up test file
                test_file.unlink()
                test_dir.rmdir()
            else:
                logger.warning("TTS basic test failed: no file created")
                
        except Exception as e:
            logger.warning(f"TTS basic test error: {str(e)}")
    
    def _get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available TTS voices"""
        try:
            if not self.tts_engine:
                return []
            
            voices = []
            available_voices = self.tts_engine.getProperty('voices')
            
            logger.info("--- Available TTS Voices ---")
            for voice in available_voices:
                voice_info = {
                    'id': voice.id,
                    'name': voice.name,
                    'gender': getattr(voice, 'gender', 'unknown'),
                    'age': getattr(voice, 'age', 'unknown')
                }
                voices.append(voice_info)
                logger.info(f"  Name: {voice_info['name']}, ID: {voice_info['id']}")
            logger.info("--------------------------")

            return voices
            
        except Exception as e:
            logger.warning(f"Error getting available voices: {str(e)}")
            return []
    
    def synthesize_speech(self, text: str, voice: str = 'default', speed: float = 1.0, session_id: str = None, slide_number: int = None) -> str:
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            voice: Voice identifier or 'default'
            speed: Speech speed multiplier (0.5-2.0)
            session_id: Session identifier for organizing files
            slide_number: Slide number for file naming
            
        Returns:
            Path to generated audio file
        """
        try:
            if not self.tts_engine:
                raise Exception("TTS engine not available")
            
            # Reset state for this attempt
            self.last_tts_error = None
            self.tts_completed = False

            # Clean text for TTS
            clean_text = self._clean_text_for_tts(text)
            logger.debug(f"TTS Input text (first 100 chars): {clean_text[:100]}...")
            
            # Configure voice
            if voice != 'default' and self.available_voices:
                voice_found = False
                logger.debug(f"Looking for voice: {voice}")
                logger.debug(f"Available voices: {[v['id'] for v in self.available_voices]}")
                
                for available_voice in self.available_voices:
                    # Try exact match first, then substring match
                    if (voice == available_voice['id'] or 
                        voice == available_voice['name'] or
                        voice in available_voice['id'] or 
                        voice in available_voice['name']):
                        logger.info(f"Setting voice to: {available_voice['name']} ({available_voice['id']})")
                        self.tts_engine.setProperty('voice', available_voice['id'])
                        voice_found = True
                        break
                
                if not voice_found:
                    logger.warning(f"Voice '{voice}' not found, using default")
            
            # Configure speed
            base_rate = 200
            adjusted_rate = int(base_rate * speed)
            adjusted_rate = max(50, min(400, adjusted_rate))  # Clamp to reasonable range
            self.tts_engine.setProperty('rate', adjusted_rate)
            logger.debug(f"TTS rate set to: {adjusted_rate}")
            
            # Generate filename with session-based organization
            if session_id and slide_number is not None:
                # Use session-based naming: slide_01.wav, slide_02.wav, etc.
                audio_dir = self._get_audio_dir(session_id)
                filename = f"slide_{slide_number:02d}.wav"
                output_path = audio_dir / filename
            else:
                # Fallback to hash-based naming for backward compatibility
                import hashlib
                text_hash = hashlib.md5(clean_text.encode()).hexdigest()[:8]
                voice_hash = hashlib.md5(voice.encode()).hexdigest()[:8]
                filename = f"tts_{text_hash}_{voice_hash}_{speed}.wav"
                # Use fallback audio directory
                audio_dir = self._get_audio_dir('fallback')
                output_path = audio_dir / filename
            
            logger.debug(f"Output path: {output_path}")
            logger.debug(f"Audio directory exists: {audio_dir.exists()}")
            
            # Synthesize speech
            logger.debug("Starting TTS synthesis...")
            self.tts_engine.save_to_file(clean_text, str(output_path))
            logger.debug("Called save_to_file, now calling runAndWait...")
            self.tts_engine.runAndWait()
            logger.debug("runAndWait completed")
            
            # Check if file was created and has content. The `tts_completed` flag can be unreliable.
            file_exists = output_path.exists()
            file_has_content = file_exists and output_path.stat().st_size > 0

            if file_has_content:
                if not self.tts_completed:
                    logger.warning(f"TTS engine reported incomplete utterance, but file was generated successfully: {output_path}")
                file_size = output_path.stat().st_size
                logger.info(f"Generated TTS audio: {output_path} (size: {file_size} bytes)")
                return str(output_path)
            else:
                logger.error("Audio file generation failed.")
                if self.last_tts_error:
                    logger.error(f"TTS engine error: {self.last_tts_error}")
                    raise Exception(f"Failed to generate audio file. Engine error: {self.last_tts_error}")
                else:
                    file_size = 0
                    if file_exists:
                        file_size = output_path.stat().st_size
                    logger.error(f"File exists: {file_exists}, TTS completed: {self.tts_completed}, File size: {file_size}")
                    raise Exception("Failed to generate audio file: File was not created or is empty.")
                
        except Exception as e:
            logger.error(f"Error synthesizing speech: {str(e)}")
            logger.error(f"TTS Engine available: {self.tts_engine is not None}")
            if self.tts_engine:
                try:
                    current_voice = self.tts_engine.getProperty('voice')
                    current_rate = self.tts_engine.getProperty('rate')
                    logger.error(f"Current voice: {current_voice}")
                    logger.error(f"Current rate: {current_rate}")
                except:
                    logger.error("Could not get TTS engine properties")
            raise
    
    def synthesize_all_speech(self, 
                                slides_content: List[Dict[str, Any]], 
                                voice: str, 
                                speed: float, 
                                session_id: str = None,
                                progress_callback: Optional[Callable[[float], None]] = None) -> List[str]:
        """
        Synthesizes speech for all transcripts in a session.
        
        Args:
            slides_content: List of slide content dictionaries.
            voice: The ID of the voice to use for TTS.
            speed: The speech rate multiplier.
            progress_callback: Optional callback for progress updates.
            
        Returns:
            A list of paths to the generated audio files.
        """
        total_slides = len(slides_content)
        audio_files = []
        
        if total_slides == 0:
            logger.warning("No slides provided for audio synthesis.")
            return []
            
        logger.info(f"Starting TTS for {total_slides} slides...")
        
        for i, slide in enumerate(slides_content):
            try:
                transcript = slide.get('transcript', '')

                if transcript:
                    audio_path = self.synthesize_speech(
                        transcript, 
                        voice, 
                        speed, 
                        session_id=session_id,
                        slide_number=i+1
                    )
                    if audio_path:
                        audio_files.append(audio_path)
                    else:
                        audio_files.append(None) # Keep list length consistent
                else:
                    logger.warning(f"No transcript for slide {i+1}, skipping audio generation.")
                    audio_files.append(None)

                if progress_callback:
                    progress = ((i + 1) / total_slides) * 100
                    progress_callback(progress)
                    
            except Exception as e:
                logger.error(f"Failed to process audio for slide {i+1}: {e}")
                audio_files.append(None)

        successful_count = len([f for f in audio_files if f])
        logger.info(f"Successfully generated {successful_count}/{total_slides} audio files.")
        return audio_files
    
    def transcribe_audio(self, audio_file) -> str:
        """
        Transcribe audio to text using Groq Whisper
        
        Args:
            audio_file: Audio file (file object or path)
            
        Returns:
            Transcribed text
        """
        try:
            if not self.groq_client:
                raise Exception("Groq client not available")
            
            # Handle different input types
            if hasattr(audio_file, 'read'):
                # File object from Flask request
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(audio_file.read())
                    temp_path = temp_file.name
                
                try:
                    with open(temp_path, 'rb') as file:
                        transcription = self.groq_client.audio.transcriptions.create(
                            file=file,
                            model="whisper-large-v3-turbo",
                            language="en",
                            response_format="text",
                            temperature=0.0
                        )
                    
                    # Clean up temp file
                    os.unlink(temp_path)
                    
                    return transcription.strip() if transcription else ""
                    
                except Exception as e:
                    # Clean up temp file on error
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    raise
            
            else:
                # File path
                with open(audio_file, 'rb') as file:
                    transcription = self.groq_client.audio.transcriptions.create(
                        file=file,
                        model="whisper-large-v3-turbo",
                        language="en",
                        response_format="text",
                        temperature=0.0
                    )
                
                return transcription.strip() if transcription else ""
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            raise
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for optimal TTS synthesis"""
        try:
            # Remove problematic characters
            cleaned = text.replace('*', '')
            cleaned = cleaned.replace('#', '')
            cleaned = cleaned.replace('_', '')
            cleaned = cleaned.replace('`', '')
            cleaned = cleaned.replace('[', '')
            cleaned = cleaned.replace(']', '')
            
            # Replace symbols with words
            cleaned = cleaned.replace('&', 'and')
            cleaned = cleaned.replace('%', 'percent')
            cleaned = cleaned.replace('@', 'at')
            cleaned = cleaned.replace('$', 'dollars')
            cleaned = cleaned.replace('+', 'plus')
            cleaned = cleaned.replace('=', 'equals')
            
            # Improve punctuation spacing
            import re
            cleaned = re.sub(r'\s+', ' ', cleaned)  # Multiple spaces to single
            cleaned = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', cleaned)  # Space after sentences
            cleaned = re.sub(r'([,:;])\s*', r'\1 ', cleaned)  # Space after punctuation
            
            # Remove extra whitespace
            cleaned = cleaned.strip()
            
            return cleaned
            
        except Exception as e:
            logger.warning(f"Error cleaning text for TTS: {str(e)}")
            return text
    
    def get_voice_list(self) -> List[Dict[str, str]]:
        """Get list of available voices"""
        return self.available_voices
    
    def get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices (API endpoint method)"""
        return self.available_voices
    
    def generate_slide_audio(self, slide_data: Dict[str, Any], options: Dict[str, Any] = None, session_id: str = None, slide_number: int = None) -> str:
        """
        Generate audio for a single slide
        
        Args:
            slide_data: Slide data containing transcript
            options: Audio generation options (voice, speed, etc.)
            
        Returns:
            Path to generated audio file
        """
        try:
            transcript = slide_data.get('transcript', '')
            if not transcript:
                raise ValueError("No transcript found in slide data")
            
            # Extract options
            if options is None:
                options = {}
            
            voice = options.get('voice', 'default')
            speed = options.get('speed', 1.0)
            
            # Generate audio using synthesize_speech for single slide
            audio_file = self.synthesize_speech(
                transcript, 
                voice, 
                speed, 
                session_id=session_id,
                slide_number=slide_number
            )
            return audio_file
            
        except Exception as e:
            logger.error(f"Error generating slide audio: {str(e)}")
            raise
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set the TTS voice
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            True if voice was set successfully
        """
        try:
            if not self.tts_engine:
                return False
            
            for voice in self.available_voices:
                if voice['id'] == voice_id:
                    self.tts_engine.setProperty('voice', voice_id)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error setting voice: {str(e)}")
            return False
    
    def cleanup_old_audio(self, max_age_hours: int = 24):
        """
        Clean up old audio files from temp/fallback directories
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            removed_count = 0
            
            # Clean up fallback audio directory if it exists
            fallback_audio_dir = self._get_audio_dir('fallback')
            if fallback_audio_dir.exists():
                for file_path in fallback_audio_dir.glob('*.wav'):
                    file_age = current_time - file_path.stat().st_mtime
                    
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old audio files")
                
        except Exception as e:
            logger.warning(f"Error cleaning up audio files: {str(e)}")