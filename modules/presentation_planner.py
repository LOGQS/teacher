#!/usr/bin/env python3
"""
Presentation Planner using Gemini-2.5-Pro
Converts hierarchical course structures into sequential presentation formats.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class PresentationPlanner:
    """Converts course structures into presentation plans using Gemini-2.5-Pro"""
    
    def __init__(self, file_manager=None):
        """Initialize the presentation planner with Gemini client"""
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-pro"
        self.file_manager = file_manager
        
    def create_plan(self, 
                   course_structure: Dict[str, Any],
                   slide_count: str = 'auto',
                   content_density: str = 'medium') -> Dict[str, Any]:
        """
        Convert course structure to presentation plan
        
        Args:
            course_structure: Hierarchical course structure from CourseGenerator
            slide_count: Target slide count ('auto' or specific number)
            content_density: Content density per slide (low, medium, high)
            
        Returns:
            Dictionary containing sequential presentation plan
        """
        try:
            session_id = course_structure.get('metadata', {}).get('session_id', 'unknown_session')
            start_time = time.time()

            # Build system instruction for presentation planning
            system_instruction = self._build_system_instruction(slide_count, content_density)
            
            # Create the main prompt with course structure
            prompt = self._build_planning_prompt(course_structure, slide_count, content_density)
            
            # Configure generation parameters
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )
            
            # Generate presentation plan
            logger.info("Converting course structure to presentation plan")
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )
            
            processing_time = time.time() - start_time
            
            # Log the interaction
            if self.file_manager:
                request_data = {'prompt': prompt, 'system_instruction': system_instruction}
                response_data = {'text': response.text}
                try:
                    response_data['usage'] = response.usage_metadata
                except Exception:
                    pass
                
                self.file_manager.save_ai_interaction_log(
                    session_id, 'presentation_planning', self.model, request_data, response_data, processing_time
                )

            # Parse and validate response
            presentation_plan = self._parse_presentation_plan(response.text)
            
            # Add metadata
            presentation_plan['metadata'] = {
                'source_course': course_structure.get('course_title', 'Unknown'),
                'slide_count_target': slide_count,
                'content_density': content_density,
                'generated_at': self._get_timestamp(),
                'model_used': self.model,
                'original_structure': course_structure.get('metadata', {})
            }
            
            logger.info(f"Successfully created presentation plan with {len(presentation_plan.get('slides', []))} slides")
            return presentation_plan
            
        except Exception as e:
            logger.error(f"Error creating presentation plan: {str(e)}")
            raise
    
    def _build_system_instruction(self, slide_count: str, content_density: str) -> str:
        """Build system instruction for presentation planning"""
        
        base_instruction = """You are an expert presentation designer and educational content strategist. Your task is to convert hierarchical course structures into sequential, engaging presentation formats that follow best practices for educational presentations.

CORE RESPONSIBILITIES:
1. Transform hierarchical course content into a logical slide sequence
2. Ensure smooth narrative flow and progressive building of concepts
3. Design slides that work well for both visual display and audio narration
4. Create engaging, professional presentation structure suitable for educational content

OUTPUT FORMAT REQUIREMENTS:
You MUST respond with a valid JSON structure containing:
- presentation_title: Main presentation title
- presentation_description: Brief description of the presentation
- estimated_duration: Total estimated presentation time
- slides: Array of slide objects, each containing:
  - slide_number: Sequential slide number (starting from 1)
  - slide_type: Type of slide (intro, content, transition, summary, conclusion)
  - title: Slide title
  - content_brief: Brief description of slide content (2-3 sentences)
  - main_points: Array of key points to cover on this slide
  - estimated_time: Estimated time for this slide (in minutes)
  - transition_note: How this slide connects to the next one
  - visual_suggestions: Suggestions for visual elements (images, diagrams, etc.)

PRESENTATION DESIGN PRINCIPLES:
1. OPENING: Start with engaging introduction that sets context and expectations
2. BUILDING: Each slide should build upon previous concepts logically
3. PACING: Vary slide content and pacing to maintain engagement
4. TRANSITIONS: Smooth transitions between topics and concepts
5. CLOSURE: Strong conclusion that reinforces key learning outcomes

SLIDE TYPES TO USE:
- intro: Course introduction and overview
- content: Main content slides covering specific topics
- transition: Bridge slides between major topics
- summary: Recap slides for major sections
- conclusion: Final summary and next steps"""

        # Add slide count specific instructions
        if slide_count.lower() == 'auto':
            count_instruction = """
SLIDE COUNT: AUTOMATIC
- Determine optimal slide count based on content complexity and depth
- Typical range: 15-40 slides for comprehensive course
- Balance thoroughness with engagement (avoid overwhelming or rushing)
- Each major topic should have 3-8 slides depending on complexity"""
        else:
            count_instruction = f"""
SLIDE COUNT: {slide_count} SLIDES
- Structure content to fit exactly within {slide_count} slides
- Distribute content evenly across available slides
- Prioritize most important concepts if content needs to be condensed
- Ensure each slide has substantial, valuable content"""

        # Add content density instructions
        density_instructions = {
            'low': """
CONTENT DENSITY: LOW
- Each slide should cover one main concept or idea
- Include more introduction and explanation slides
- Allow more time for each concept to be thoroughly explained
- Include more transition and summary slides""",
            'medium': """
CONTENT DENSITY: MEDIUM
- Balance between thoroughness and efficiency
- Each slide can cover 1-2 related concepts
- Include adequate explanation without being verbose
- Standard pacing suitable for most audiences""",
            'high': """
CONTENT DENSITY: HIGH
- Pack more information into each slide efficiently
- Cover multiple related concepts per slide when appropriate
- Assume audience can handle faster pacing
- Focus on core concepts with less repetition"""
        }
        
        full_instruction = f"""{base_instruction}

{count_instruction}

{density_instructions.get(content_density, density_instructions['medium'])}

QUALITY STANDARDS:
- Ensure logical progression that builds understanding step by step
- Create engaging flow that maintains audience interest
- Balance visual and audio elements appropriately
- Design for both educational value and professional presentation quality
- Consider timing to avoid rushing or dragging

Remember: Output ONLY valid JSON. No additional text, explanations, or formatting."""
        
        return full_instruction
    
    def _build_planning_prompt(self, 
                             course_structure: Dict[str, Any],
                             slide_count: str,
                             content_density: str) -> str:
        """Build the main prompt for presentation planning"""
        
        # Extract key information from course structure
        course_title = course_structure.get('course_title', 'Unknown Course')
        main_topics = course_structure.get('main_topics', [])
        
        prompt = f"""Convert the following course structure into a sequential presentation plan:

COURSE: {course_title}
TARGET SLIDES: {slide_count}
CONTENT DENSITY: {content_density}

COURSE STRUCTURE:
{json.dumps(course_structure, indent=2)}

Create a presentation plan that:
1. Transforms this hierarchical structure into a logical slide sequence
2. Ensures smooth flow from introduction to conclusion
3. Builds concepts progressively without overwhelming the audience
4. Includes appropriate transitions between major topics
5. Balances content depth with presentation timing

The presentation should be suitable for both visual display and audio narration, with each slide designed to be self-contained yet part of a cohesive whole.

Respond with valid JSON only."""
        
        return prompt
    
    def _parse_presentation_plan(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate the presentation plan response"""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            presentation_plan = json.loads(cleaned_text)
            
            # Validate required fields
            required_fields = ['presentation_title', 'slides']
            for field in required_fields:
                if field not in presentation_plan:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate slides structure
            for i, slide in enumerate(presentation_plan['slides']):
                required_slide_fields = ['slide_number', 'title', 'content_brief']
                for field in required_slide_fields:
                    if field not in slide:
                        raise ValueError(f"Missing required field '{field}' in slide {i+1}")
                
                # Ensure slide numbers are sequential
                if slide['slide_number'] != i + 1:
                    slide['slide_number'] = i + 1
            
            return presentation_plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Response text: {response_text}")
            raise ValueError("Invalid JSON response from model")
        except Exception as e:
            logger.error(f"Error parsing presentation plan: {str(e)}")
            raise
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_plan_summary(self, presentation_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the presentation plan"""
        try:
            slides = presentation_plan.get('slides', [])
            slide_count = len(slides)
            
            # Count slide types
            slide_types = {}
            total_time = 0
            
            for slide in slides:
                slide_type = slide.get('slide_type', 'content')
                slide_types[slide_type] = slide_types.get(slide_type, 0) + 1
                
                # Extract time estimate
                time_str = slide.get('estimated_time', '2')
                try:
                    if isinstance(time_str, str):
                        time_val = float(time_str.split()[0])
                    else:
                        time_val = float(time_str)
                    total_time += time_val
                except:
                    total_time += 2  # Default 2 minutes per slide
            
            return {
                'presentation_title': presentation_plan.get('presentation_title', 'Unknown'),
                'total_slides': slide_count,
                'estimated_duration_minutes': total_time,
                'slide_types': slide_types,
                'average_time_per_slide': round(total_time / slide_count, 1) if slide_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating plan summary: {str(e)}")
            return {'error': 'Failed to generate summary'}