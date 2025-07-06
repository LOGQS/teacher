#!/usr/bin/env python3
"""
Conversation Manager - Interactive Q&A System
Handles real-time question answering and conversational AI interactions during presentations.
"""

import os
import logging
import base64
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from google import genai
from PIL import Image
import io

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages interactive Q&A conversations during presentations"""
    
    def __init__(self, file_manager=None):
        """Initialize the conversation manager"""
        self.file_manager = file_manager
        # Initialize Gemini API
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=api_key)
        
        # Conversation history storage
        self.conversation_history = {}
        # Gemini chat sessions for maintaining context
        self.chat_sessions = {}
        
        # System instruction for teacher mode
        self.system_instruction = """
You are an expert educational AI teacher assistant. You are helping a student during an interactive presentation.

CONTEXT:
- The student is viewing a specific slide in an educational presentation
- You have access to the slide's visual content (screenshot) and its transcript
- You can see the conversation history to maintain context
- The student may ask questions about the current slide or related topics

YOUR ROLE:
- Act as a knowledgeable, patient, and encouraging teacher
- Provide clear, educational explanations appropriate for the student's level
- Use the slide content and transcript to inform your responses
- Encourage deeper understanding and critical thinking
- Relate concepts to real-world applications when helpful
- Keep responses concise but thorough (2-4 sentences usually)

RESPONSE GUIDELINES:
- Be conversational and approachable
- Use simple, clear language
- Provide examples when helpful
- If uncertain about something, acknowledge it honestly
- Encourage follow-up questions
- Stay focused on educational content

IMPORTANT:
- Do not provide information that contradicts the slide content unless it's clearly incorrect
- Reference the slide content when relevant
- Build on the presentation's learning objectives
- Maintain educational focus - avoid off-topic conversations
"""
    
    def start_conversation(self, session_id: str, slide_context: Dict[str, Any]) -> str:
        """
        Start a new conversation session
        
        Args:
            session_id: Unique identifier for the conversation session
            slide_context: Context about the current slide
            
        Returns:
            Session ID for the conversation
        """
        try:
            # Create Gemini chat session with system instruction
            from google.genai import types
            
            chat_session = self.client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction
                )
            )
            
            self.chat_sessions[session_id] = chat_session
            self.conversation_history[session_id] = {
                'messages': [],
                'slide_context': slide_context,
                'created_at': self._get_timestamp()
            }
            
            logger.info(f"Started conversation session with Gemini chat: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            raise
    
    def ask_question(self, 
                    session_id: str, 
                    question: str, 
                    slide_screenshot: Optional[str] = None,
                    slide_transcript: Optional[str] = None,
                    slide_image_url: Optional[str] = None) -> str:
        """
        Process a student question and generate response
        
        Args:
            session_id: Conversation session identifier
            question: Student's question
            slide_screenshot: Base64 encoded screenshot of current slide
            slide_transcript: Transcript text for the current slide
            slide_image_url: URL to the slide image from backend
            
        Returns:
            AI response to the question
        """
        try:
            # Get or create conversation history and chat session
            if session_id not in self.conversation_history:
                self.conversation_history[session_id] = {
                    'messages': [],
                    'slide_context': {},
                    'created_at': self._get_timestamp()
                }
                
                # Create chat session if not exists
                from google.genai import types
                chat_session = self.client.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction
                    )
                )
                self.chat_sessions[session_id] = chat_session
            
            conversation = self.conversation_history[session_id]
            chat_session = self.chat_sessions[session_id]
            
            # Build context for the AI
            context_parts = []
            
            # Add system instruction
            context_parts.append(self.system_instruction)
            
            # Add slide context
            if slide_transcript:
                context_parts.append(f"\n--- CURRENT SLIDE TRANSCRIPT ---\n{slide_transcript}\n")
            
            # Add conversation history
            if conversation['messages']:
                context_parts.append("\n--- CONVERSATION HISTORY ---")
                for msg in conversation['messages'][-6:]:  # Last 6 messages for context
                    context_parts.append(f"{msg['role'].title()}: {msg['content']}")
                context_parts.append("")
            
            # Add current question
            context_parts.append(f"\n--- STUDENT QUESTION ---\n{question}\n")
            
            # Prepare content for API call
            content_parts = ["\n".join(context_parts)]
            
            # Add slide image if available
            slide_image = None
            
            # Try base64 screenshot first
            if slide_screenshot:
                try:
                    image_data = base64.b64decode(slide_screenshot)
                    slide_image = Image.open(io.BytesIO(image_data))
                    logger.debug("Using base64 slide screenshot")
                except Exception as e:
                    logger.warning(f"Error processing slide screenshot: {str(e)}")
            
            # Fallback to slide image URL from backend
            elif slide_image_url:
                try:
                    # Convert relative URL to local file path
                    if slide_image_url.startswith('/api/images/'):
                        # Extract file path from URL
                        file_path = slide_image_url.replace('/api/images/', '')
                        local_path = Path(file_path)
                        
                        if local_path.exists():
                            slide_image = Image.open(local_path)
                            logger.debug(f"Using slide image from: {local_path}")
                        else:
                            logger.warning(f"Slide image file not found: {local_path}")
                except Exception as e:
                    logger.warning(f"Error loading slide image from URL: {str(e)}")
            
            # Prepare message content for chat
            message_content = []
            
            # Add context and question text
            message_content.append("\n".join(context_parts))
            
            # Add the image to content if we have one
            if slide_image:
                message_content.append(slide_image)
            
            # Send message to chat session (maintains conversation history automatically)
            response = chat_session.send_message(message_content)
            
            answer = response.text.strip()
            
            # Store conversation
            conversation['messages'].extend([
                {
                    'role': 'student',
                    'content': question,
                    'timestamp': self._get_timestamp()
                },
                {
                    'role': 'teacher',
                    'content': answer,
                    'timestamp': self._get_timestamp()
                }
            ])
            
            # Update slide context
            if slide_transcript:
                conversation['slide_context']['transcript'] = slide_transcript
            if slide_screenshot:
                conversation['slide_context']['has_screenshot'] = True
            
            logger.info(f"Processed question in session {session_id}")
            return answer
            
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return "I apologize, but I'm having trouble processing your question right now. Please try again."
    
    def get_conversation_history(self, session_id: str) -> Dict[str, Any]:
        """
        Get conversation history for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Conversation history dictionary
        """
        return self.conversation_history.get(session_id, {
            'messages': [],
            'slide_context': {},
            'created_at': self._get_timestamp()
        })
    
    def end_conversation(self, session_id: str) -> bool:
        """
        End a conversation session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was ended successfully
        """
        try:
            if session_id in self.conversation_history:
                # Log conversation stats
                messages = self.conversation_history[session_id]['messages']
                student_questions = len([m for m in messages if m['role'] == 'student'])
                
                logger.info(f"Ending conversation session {session_id} - {student_questions} questions asked")
                
                # Optional: Save conversation to file for analysis
                self._save_conversation_log(session_id, self.conversation_history[session_id])
                
                # Clean up from memory
                del self.conversation_history[session_id]
                
                # Clean up chat session (Gemini automatically handles history cleanup)
                if session_id in self.chat_sessions:
                    del self.chat_sessions[session_id]
                    logger.debug(f"Cleaned up chat session for {session_id}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error ending conversation: {str(e)}")
            return False
    
    def update_slide_context(self, 
                           session_id: str, 
                           slide_transcript: Optional[str] = None,
                           slide_screenshot: Optional[str] = None) -> bool:
        """
        Update slide context for ongoing conversation
        
        Args:
            session_id: Session identifier
            slide_transcript: New slide transcript
            slide_screenshot: New slide screenshot
            
        Returns:
            True if context was updated successfully
        """
        try:
            if session_id not in self.conversation_history:
                return False
            
            conversation = self.conversation_history[session_id]
            
            if slide_transcript:
                conversation['slide_context']['transcript'] = slide_transcript
            
            if slide_screenshot:
                conversation['slide_context']['has_screenshot'] = True
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating slide context: {str(e)}")
            return False
    
    
    def _save_conversation_log(self, session_id: str, conversation: Dict[str, Any]):
        """Save conversation log to file"""
        try:
            if self.file_manager:
                # Use session-based logs directory
                subdirs = self.file_manager.get_session_subdirs(session_id)
                logs_dir = subdirs['logs']
                log_file = logs_dir / f"conversation_summary.json"
            else:
                # Fallback to old structure
                logs_dir = Path('data/conversation_logs')
                logs_dir.mkdir(parents=True, exist_ok=True)
                log_file = logs_dir / f"conversation_{session_id}.json"
            
            import json
            with open(log_file, 'w') as f:
                # Remove screenshot data before saving
                conversation_copy = conversation.copy()
                if 'slide_context' in conversation_copy:
                    conversation_copy['slide_context'].pop('has_screenshot', None)
                
                json.dump(conversation_copy, f, indent=2)
            
            logger.debug(f"Saved conversation log: {log_file}")
            
        except Exception as e:
            logger.warning(f"Error saving conversation log: {str(e)}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def cleanup_old_conversations(self, max_age_hours: int = 24):
        """
        Clean up old conversation sessions from memory
        
        Args:
            max_age_hours: Maximum age of conversations to keep
        """
        try:
            from datetime import datetime, timedelta
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            sessions_to_remove = []
            
            for session_id, conversation in self.conversation_history.items():
                try:
                    created_at = datetime.fromisoformat(conversation.get('created_at', ''))
                    if created_at < cutoff_time:
                        sessions_to_remove.append(session_id)
                except (ValueError, TypeError):
                    # If timestamp is invalid, remove the session
                    sessions_to_remove.append(session_id)
            
            # Remove old sessions
            for session_id in sessions_to_remove:
                self.end_conversation(session_id)
            
            if sessions_to_remove:
                logger.info(f"Cleaned up {len(sessions_to_remove)} old conversation sessions")
                
        except Exception as e:
            logger.warning(f"Error cleaning up conversations: {str(e)}")