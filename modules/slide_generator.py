#!/usr/bin/env python3
"""
Slide Content Generator using Gemini-2.5-Flash
Generates detailed slide content including transcript, layout, and visual specifications.
"""

import os
import json
import logging
import time
import re
from typing import Dict, List, Any, Optional, Callable
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class SlideGenerator:
    """Generates detailed slide content using Gemini-2.5-Flash"""
    
    def __init__(self, file_manager=None):
        """Initialize the slide generator with Gemini client"""
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.file_manager = file_manager
        
        # Rate limiting for Gemini 2.5 Flash: 10 RPM, 250,000 TPM, 250 RPD
        self.max_requests_per_minute = 10
        self.request_times = []
        
    def _clean_json_from_response(self, text: str) -> str:
        """
        Extracts a JSON string from a larger text block, removing markdown 
        and any text outside the main JSON object/array.
        """
        # Find the start of the first JSON object or array
        text = text.strip()
        
        # Remove markdown fences
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```', '', text)
        
        start_bracket = text.find('[')
        start_brace = text.find('{')
        
        if start_bracket == -1 and start_brace == -1:
            logger.warning("No JSON object or array found in the response.")
            return text

        start_pos = -1
        if start_bracket != -1 and start_brace != -1:
            start_pos = min(start_bracket, start_brace)
        elif start_bracket != -1:
            start_pos = start_bracket
        else:
            start_pos = start_brace
            
        # Find the corresponding end
        if text[start_pos] == '[':
            end_char = ']'
        else:
            end_char = '}'
        
        end_pos = text.rfind(end_char)

        if end_pos > start_pos:
            return text[start_pos:end_pos+1]
            
        logger.warning("Could not find matching end for JSON object/array.")
        return text

    def generate_all_slides(self, 
                           presentation_plan: Dict[str, Any],
                           batch_size: int = 5,
                           progress_callback: Optional[Callable[[float], None]] = None) -> List[Dict[str, Any]]:
        """
        Generate content for all slides in the presentation plan
        
        Args:
            presentation_plan: Presentation plan from PresentationPlanner
            batch_size: Number of slides to generate per API call (1-10)
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of detailed slide content dictionaries
        """
        try:
            slides = presentation_plan.get('slides', [])
            total_slides = len(slides)
            generated_slides = []
            session_id = presentation_plan.get('session_id', 'unknown_session')
            
            logger.info(f"Generating content for {total_slides} slides in batches of {batch_size}")
            
            # Process slides in batches
            for i in range(0, total_slides, batch_size):
                batch_slides = slides[i:i + batch_size]
                
                # Apply rate limiting
                self._apply_rate_limit()
                
                # Generate content for this batch
                batch_content = self._generate_batch_content(
                    batch_slides, 
                    presentation_plan.get('presentation_title', 'Presentation'),
                    i + 1,  # Starting slide number
                    session_id
                )
                
                generated_slides.extend(batch_content)
                
                # Update progress
                progress = (len(generated_slides) / total_slides) * 100
                if progress_callback:
                    progress_callback(progress)
                
                logger.info(f"Generated content for slides {i+1}-{min(i+batch_size, total_slides)} ({len(generated_slides)}/{total_slides})")
            
            return generated_slides
            
        except Exception as e:
            logger.error(f"Error generating slides: {str(e)}")
            raise
    
    def _generate_batch_content(self, 
                               slides_batch: List[Dict[str, Any]],
                               presentation_title: str,
                               start_number: int,
                               session_id: str) -> List[Dict[str, Any]]:
        """Generate content for a batch of slides"""
        try:
            start_time = time.time()
            
            # Build system instruction
            system_instruction = self._build_system_instruction()
            
            # Create prompt for batch
            prompt = self._build_batch_prompt(slides_batch, presentation_title, start_number)
            
            # Configure generation with grounding
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[grounding_tool],
            )
            
            # Generate content
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )
            
            processing_time = time.time() - start_time
            
            # Log the interaction for this batch
            if self.file_manager:
                request_data = {
                    'prompt': prompt, 
                    'system_instruction': str(system_instruction),
                    'config': str(config)
                }
                batch_name = f"slide_generation_batch_{start_number}-{start_number + len(slides_batch) - 1}"
                self.file_manager.save_ai_interaction_log(
                    session_id=session_id, 
                    stage=batch_name, 
                    model_name=self.model, 
                    request_data=request_data,
                    response_data=response, 
                    processing_time=processing_time,
                    usage_metadata=getattr(response, 'usage_metadata', None)
                )
            
            # Parse response
            batch_content = self._parse_batch_response(response.text, len(slides_batch))
            
            return batch_content
            
        except Exception as e:
            logger.error(f"Error generating batch content: {str(e)}")
            raise
    
    def _build_system_instruction(self) -> str:
        """Build comprehensive system instruction for slide generation"""
        
        return """You are an expert educational content creator and presentation designer. Your task is to generate detailed, engaging slide content that includes transcript, layout specifications, and visual elements for educational presentations.

CORE RESPONSIBILITIES:
1. Generate natural, conversational transcript text suitable for text-to-speech conversion
2. Create structured slide layouts with precise positioning and formatting
3. Specify visual elements, images, and design components
4. Ensure educational value and professional presentation quality

OUTPUT FORMAT REQUIREMENTS:
You MUST respond with a valid JSON array containing slide objects. Each slide object must include:

- slide_number: Sequential slide number
- title: Slide title
- transcript: Natural spoken narration text (NO special characters, pure text for TTS)
- layout: Layout specification object containing:
  - slide_type: Type (title_slide, content_slide, comparison_slide, etc.)
  - background_color: Background color specification
  - elements: Array of slide elements, each with:
    - type: Element type (textbox, image, shape, chart)
    - position: {x, y, width, height} in inches
    - content: Text content or description
    - formatting: Font, size, color, alignment specifications
- images: Array of image specifications:
  - position: {x, y, width, height} in inches
  - description: Detailed description for image search/generation
  - alt_text: Accessibility text
  - caption: Optional caption text
- visual_notes: Additional design notes and suggestions

TRANSCRIPT GUIDELINES:
- Write in conversational, teacher-like tone suitable for audio narration
- Avoid reading slide content directly - provide explanatory insights
- No mathematical formulas in spoken format (describe concepts instead)
- No markdown, special characters, or formatting that interferes with TTS
- Use natural punctuation and pacing for smooth speech delivery
- Aim for 150-250 words per slide (roughly 1-2 minutes of speech)

LAYOUT GUIDELINES:
- Use standard PowerPoint slide dimensions (10" x 7.5")
- Position elements clearly without overlap
- Ensure readability with appropriate font sizes (minimum 16pt for body text)
- Follow visual hierarchy principles
- Leave appropriate white space
- Consider both visual display and audio narration needs

VISUAL ELEMENT SPECIFICATIONS:
- Textbox elements: Specify exact positioning, font, size, color
- Image elements: Provide detailed descriptions for search/generation
- Shape elements: Specify type, color, positioning
- Chart elements: Specify data visualization needs

EDUCATIONAL DESIGN PRINCIPLES:
- Each slide should have clear learning objective
- Build concepts progressively
- Use appropriate visual aids to support learning
- Balance text and visual elements
- Ensure accessibility and professional appearance

IMPORTANT: Output ONLY valid JSON array. No additional text, explanations, or formatting."""
    
    def _build_batch_prompt(self, 
                           slides_batch: List[Dict[str, Any]],
                           presentation_title: str,
                           start_number: int) -> str:
        """Build prompt for batch slide generation"""
        
        prompt = f"""Generate detailed slide content for the following slides from the presentation: "{presentation_title}"

SLIDES TO GENERATE:
"""
        
        for i, slide in enumerate(slides_batch):
            slide_num = start_number + i
            prompt += f"""
Slide {slide_num}:
- Title: {slide.get('title', 'Untitled')}
- Type: {slide.get('slide_type', 'content')}
- Content Brief: {slide.get('content_brief', '')}
- Main Points: {', '.join(slide.get('main_points', []))}
- Estimated Time: {slide.get('estimated_time', '2 minutes')}
- Visual Suggestions: {slide.get('visual_suggestions', 'Standard educational visuals')}
"""
        
        prompt += f"""

REQUIREMENTS:
1. Generate comprehensive content for each slide including transcript, layout, and visual specifications
2. Ensure smooth narrative flow between slides
3. Use Google Search grounding when needed for accurate, current information
4. Create engaging, educational content suitable for university-level learning
5. Design for both visual presentation and audio narration

Create detailed slide content that transforms these brief descriptions into complete, professional presentation slides.

Respond with valid JSON array only."""
        
        return prompt
    
    def _parse_batch_response(self, response_text: str, expected_count: int) -> List[Dict[str, Any]]:
        """Parse and validate batch response"""
        try:
            cleaned_text = self._clean_json_from_response(response_text)
            
            # Parse JSON
            slides_content = json.loads(cleaned_text)
            
            # Ensure it's an array
            if not isinstance(slides_content, list):
                raise ValueError("Response must be a JSON array of slides")
            
            # Validate each slide
            for i, slide in enumerate(slides_content):
                required_fields = ['slide_number', 'title', 'transcript', 'layout']
                for field in required_fields:
                    if field not in slide:
                        raise ValueError(f"Missing required field '{field}' in slide {i+1}")
                
                # Validate layout structure
                layout = slide.get('layout', {})
                if 'elements' not in layout:
                    layout['elements'] = []
                
                # Ensure images array exists
                if 'images' not in slide:
                    slide['images'] = []
                
                # Clean transcript for TTS
                slide['transcript'] = self._clean_transcript_for_tts(slide['transcript'])
            
            return slides_content
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Original response text: {response_text}")
            logger.error(f"Cleaned response text: {cleaned_text}")
            raise ValueError("Invalid JSON response from model") from e
        except Exception as e:
            logger.error(f"Error parsing batch response: {str(e)}")
            raise
    
    def _clean_transcript_for_tts(self, transcript: str) -> str:
        """Clean transcript text for optimal TTS conversion"""
        try:
            # Remove problematic characters
            cleaned = transcript.replace('*', '')
            cleaned = cleaned.replace('#', '')
            cleaned = cleaned.replace('_', '')
            cleaned = cleaned.replace('`', '')
            
            # Replace symbols with words
            cleaned = cleaned.replace('&', 'and')
            cleaned = cleaned.replace('%', 'percent')
            cleaned = cleaned.replace('@', 'at')
            cleaned = cleaned.replace('$', 'dollars')
            
            # Ensure proper spacing around punctuation
            cleaned = re.sub(r'\s+', ' ', cleaned)  # Multiple spaces to single
            cleaned = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', cleaned)  # Space after sentence endings
            
            return cleaned.strip()
            
        except Exception as e:
            logger.warning(f"Error cleaning transcript: {str(e)}")
            return transcript
    
    def _apply_rate_limit(self):
        """Apply rate limiting for Gemini 2.5 Flash"""
        current_time = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        # If we're at the limit, wait
        if len(self.request_times) >= self.max_requests_per_minute:
            wait_time = 60 - (current_time - self.request_times[0]) + 1
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
        
        # Record this request
        self.request_times.append(current_time)
    
    def get_generation_summary(self, slides_content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of slide generation results"""
        try:
            total_slides = len(slides_content)
            total_transcript_words = sum(
                len(slide.get('transcript', '').split()) 
                for slide in slides_content
            )
            
            # Count elements
            total_textboxes = sum(
                len([e for e in slide.get('layout', {}).get('elements', []) if e.get('type') == 'textbox'])
                for slide in slides_content
            )
            
            total_images = sum(
                len(slide.get('images', []))
                for slide in slides_content
            )
            
            # Estimate audio duration (average 150 words per minute)
            estimated_audio_minutes = total_transcript_words / 150
            
            return {
                'total_slides': total_slides,
                'total_transcript_words': total_transcript_words,
                'estimated_audio_duration_minutes': round(estimated_audio_minutes, 1),
                'total_textboxes': total_textboxes,
                'total_images': total_images,
                'average_words_per_slide': round(total_transcript_words / total_slides, 1) if total_slides > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {'error': 'Failed to generate summary'}