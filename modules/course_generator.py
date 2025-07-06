#!/usr/bin/env python3
"""
Course Structure Generator using Gemini-2.5-Pro
Generates hierarchical course structures based on user input and customizations.
"""

import dotenv
import json
import logging
import time
from typing import Dict, Any
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class CourseGenerator:
    """Generates comprehensive course structures using Gemini-2.5-Pro"""
    
    def __init__(self, file_manager=None):
        """Initialize the course generator with Gemini client"""
        dotenv.load_dotenv()
        api_key = dotenv.get_key('.env', 'GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-pro"
        self.file_manager = file_manager
        
        # Rate limiting tracking
        self.request_count = 0
        self.last_request_time = 0
        
    def generate_structure(self, 
                         topic: str,
                         complexity: str,
                         duration: str,
                         learning_style: str,
                         customizations: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive course structure
        
        Args:
            topic: The main learning topic
            complexity: Complexity level (beginner, intermediate, advanced)
            duration: Desired course duration or slide count
            learning_style: Learning style preference (visual, auditory, mixed)
            customizations: Additional customization options
            
        Returns:
            Dictionary containing hierarchical course structure
        """
        try:
            session_id = customizations.get('session_id', 'unknown_session')
            start_time = time.time()
            
            # Build system instruction based on customizations
            system_instruction = self._build_system_instruction(
                complexity, duration, learning_style, customizations or {}
            )
            
            # Create the main prompt
            prompt = self._build_main_prompt(topic, complexity, duration, learning_style, customizations)
            
            # Configure generation parameters
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )
            
            # Generate course structure
            logger.info(f"Generating course structure for topic: {topic}")
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )
            
            processing_time = time.time() - start_time
            
            # Log the interaction
            if self.file_manager:
                request_data = {'prompt': prompt, 'system_instruction': system_instruction}
                # Ensure response is serializable
                response_data = {'text': response.text}
                try:
                    # Try to get full response attributes
                    response_data['usage'] = response.usage_metadata
                except Exception:
                    pass # Ignore if not available
                
                self.file_manager.save_ai_interaction_log(
                    session_id, 'course_structure', self.model, request_data, response_data, processing_time
                )
            
            # Parse and validate response
            course_structure = self._parse_course_structure(response.text)
            
            # Add metadata
            course_structure['metadata'] = {
                'topic': topic,
                'complexity': complexity,
                'duration': duration,
                'learning_style': learning_style,
                'customizations': customizations,
                'generated_at': self._get_timestamp(),
                'model_used': self.model
            }
            
            logger.info(f"Successfully generated course structure with {len(course_structure.get('main_topics', []))} main topics")
            return course_structure
            
        except Exception as e:
            logger.error(f"Error generating course structure: {str(e)}")
            raise
    
    def _build_system_instruction(self, 
                                complexity: str,
                                duration: str, 
                                learning_style: str,
                                customizations: Dict[str, Any]) -> str:
        """Build comprehensive system instruction for course generation"""
        
        base_instruction = """You are an expert educational curriculum designer and university-level instructor. Your task is to create comprehensive, well-structured course outlines that rival the quality of top universities.

CORE RESPONSIBILITIES:
1. Generate hierarchical course structures with main topics, subtopics, and granular learning units
2. Ensure progressive learning that builds from foundational concepts to advanced applications
3. Adapt content depth and breadth based on complexity level and duration requirements
4. Create educationally sound progression that follows established pedagogical principles

OUTPUT FORMAT REQUIREMENTS:
You MUST respond with a valid JSON structure containing:
- course_title: Main course title
- course_description: Brief description of what students will learn
- main_topics: Array of main topic objects, each containing:
  - title: Topic title
  - description: Brief description
  - subtopics: Array of subtopic objects, each containing:
    - title: Subtopic title
    - description: Brief description
    - learning_units: Array of specific learning objectives/units
    - estimated_time: Estimated time to cover this subtopic
- total_estimated_time: Total course duration
- prerequisites: Array of recommended prerequisites
- learning_outcomes: Array of specific learning outcomes students will achieve"""

        # Add complexity-specific instructions
        complexity_instructions = {
            'beginner': """
COMPLEXITY LEVEL: BEGINNER
- Start with fundamental concepts and basic terminology
- Include more foundational background and context
- Progress gradually with clear explanations at each step
- Include practical examples and real-world applications
- Ensure no prerequisite knowledge is assumed""",
            'intermediate': """
COMPLEXITY LEVEL: INTERMEDIATE
- Assume basic familiarity with core concepts
- Focus on practical applications and deeper understanding
- Include connections between concepts and cross-topic relationships
- Balance theory with hands-on examples
- Build towards more complex problem-solving scenarios""",
            'advanced': """
COMPLEXITY LEVEL: ADVANCED
- Assume strong foundational knowledge
- Focus on complex applications, edge cases, and advanced techniques
- Include current research, emerging trends, and cutting-edge developments
- Emphasize critical thinking, analysis, and original application
- Prepare for professional-level competency"""
        }
        
        # Add learning style adaptations
        learning_style_instructions = {
            'visual': """
LEARNING STYLE: VISUAL PREFERENCE
- Structure content to support visual learning with diagrams, charts, and visual examples
- Include topics that benefit from visual representation
- Plan for infographics, flowcharts, and visual comparisons
- Emphasize spatial relationships and visual patterns""",
            'auditory': """
LEARNING STYLE: AUDITORY PREFERENCE
- Structure content for excellent spoken presentation
- Include discussion topics, verbal explanations, and conversational elements
- Plan for storytelling, analogies, and verbal examples
- Emphasize clear logical flow for audio presentation""",
            'mixed': """
LEARNING STYLE: MIXED APPROACH
- Balance visual and auditory elements
- Include varied presentation methods for different learning preferences
- Plan for both visual aids and strong verbal explanations
- Accommodate different learning preferences throughout the course"""
        }
        
        # Add duration-specific instructions
        if 'slide' in duration.lower():
            duration_instruction = f"""
DURATION: {duration}
- Structure content to fit the specified slide count
- Each main topic should translate to approximately 3-6 slides
- Each subtopic should translate to 1-2 slides
- Plan content density appropriate for slide-based presentation"""
        else:
            duration_instruction = f"""
DURATION: {duration}
- Structure content to fit within the specified time frame
- Balance depth and breadth appropriate for the duration
- Ensure adequate time for each topic without rushing
- Include time estimates for each section"""
        
        # Add customization-specific instructions
        customization_instructions = ""
        if customizations:
            if customizations.get('theoretical_focus'):
                customization_instructions += "\n- Emphasize theoretical foundations and conceptual understanding"
            if customizations.get('practical_focus'):
                customization_instructions += "\n- Focus on practical applications and hands-on learning"
            if customizations.get('prerequisites_included'):
                customization_instructions += "\n- Include prerequisite concepts within the course structure"
            if customizations.get('specialized_focus'):
                customization_instructions += f"\n- Specialize in: {customizations.get('specialized_focus')}"
        
        # Combine all instructions
        full_instruction = f"""{base_instruction}

{complexity_instructions.get(complexity, '')}

{learning_style_instructions.get(learning_style, '')}

{duration_instruction}
{customization_instructions}

QUALITY STANDARDS:
- Ensure university-level academic rigor
- Create logical learning progression
- Include diverse topics that provide comprehensive coverage
- Balance foundational concepts with practical applications
- Generate content that would be suitable for professional development

Remember: Output ONLY valid JSON. No additional text, explanations, or formatting."""
        
        return full_instruction
    
    def _build_main_prompt(self, 
                          topic: str,
                          complexity: str,
                          duration: str,
                          learning_style: str,
                          customizations: Dict[str, Any]) -> str:
        """Build the main prompt for course generation"""
        
        prompt = f"""Create a comprehensive course structure for the topic: "{topic}"

REQUIREMENTS:
- Complexity Level: {complexity}
- Duration/Scope: {duration}
- Learning Style: {learning_style}"""
        
        if customizations:
            prompt += "\n\nADDITIONAL CUSTOMIZATIONS:"
            for key, value in customizations.items():
                if value:
                    prompt += f"\n- {key.replace('_', ' ').title()}: {value}"
        
        prompt += """

Generate a detailed course structure that covers this topic comprehensively. The structure should be educationally sound, progressively building from foundational concepts to advanced applications.

Respond with valid JSON only."""
        
        return prompt
    
    def _parse_course_structure(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate the course structure response"""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            course_structure = json.loads(cleaned_text)
            
            # Validate required fields
            required_fields = ['course_title', 'main_topics']
            for field in required_fields:
                if field not in course_structure:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate main topics structure
            for topic in course_structure['main_topics']:
                if 'title' not in topic or 'subtopics' not in topic:
                    raise ValueError("Invalid main topic structure")
                
                for subtopic in topic['subtopics']:
                    if 'title' not in subtopic:
                        raise ValueError("Invalid subtopic structure")
            
            return course_structure
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Response text: {response_text}")
            raise ValueError("Invalid JSON response from model")
        except Exception as e:
            logger.error(f"Error parsing course structure: {str(e)}")
            raise
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_structure_summary(self, course_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the course structure"""
        try:
            main_topics_count = len(course_structure.get('main_topics', []))
            subtopics_count = sum(
                len(topic.get('subtopics', []))
                for topic in course_structure.get('main_topics', [])
            )
            learning_units_count = sum(
                len(subtopic.get('learning_units', []))
                for topic in course_structure.get('main_topics', [])
                for subtopic in topic.get('subtopics', [])
            )
            
            return {
                'course_title': course_structure.get('course_title', 'Unknown'),
                'main_topics_count': main_topics_count,
                'subtopics_count': subtopics_count,
                'learning_units_count': learning_units_count,
                'estimated_duration': course_structure.get('total_estimated_time', 'Unknown'),
                'complexity': course_structure.get('metadata', {}).get('complexity', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"Error generating structure summary: {str(e)}")
            return {'error': 'Failed to generate summary'}