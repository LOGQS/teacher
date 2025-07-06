#!/usr/bin/env python3
"""
Image Manager - Search, generate, and process images for presentations
Handles image search, AI evaluation, and quality assessment following the correct workflow.
"""

import os
import logging
import shutil
import requests
import urllib.parse
import time
import random
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from google import genai
from PIL import Image

logger = logging.getLogger(__name__)

class ImageDownloader:
    """Production-ready image downloader with multiple provider fallback."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.downloaded_hashes = set()
        self.temp_dir = None
    
    def download_images_for_evaluation(self, query: str, image_count: int = 5) -> List[str]:
        """
        Download images for AI evaluation.
        
        Args:
            query: Search term for images
            image_count: Number of images to download for evaluation
            
        Returns:
            List of paths to downloaded images
        """
        # Create temporary directory for processing
        self.temp_dir = tempfile.mkdtemp()
        
        try:
            logger.info(f"Searching for {image_count} images for evaluation: '{query}'")
            
            # Provider fallback chain
            providers = [
                self._download_with_requests_fallback,
            ]
            
            all_temp_images = []
            
            for i, provider_func in enumerate(providers):
                try:
                    logger.debug(f"Trying provider {i+1}/{len(providers)}: {provider_func.__name__}")
                    temp_images = provider_func(query, image_count)
                    
                    if temp_images:
                        all_temp_images.extend(temp_images)
                        logger.info(f"Provider {i+1} downloaded {len(temp_images)} images")
                        break
                    else:
                        logger.warning(f"Provider {i+1} failed to download images")
                        
                except Exception as e:
                    logger.error(f"Provider {i+1} failed: {str(e)}")
                    continue
            
            return all_temp_images[:image_count]  # Return only requested number
            
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            return []
    
    def _download_with_requests_fallback(self, query: str, count: int) -> List[str]:
        """Fallback method using direct requests to search engines."""
        try:
            from bs4 import BeautifulSoup
            
            temp_subdir = os.path.join(self.temp_dir, 'requests')
            os.makedirs(temp_subdir, exist_ok=True)
            
            # Search Bing Images
            search_url = f"https://www.bing.com/images/search?q={query}&count={count}"
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            img_tags = soup.find_all('img', limit=count * 2)  # Get more to filter
            
            files = []
            for i, img in enumerate(img_tags[:count * 2]):
                if len(files) >= count:
                    break
                    
                img_url = img.get('src') or img.get('data-src')
                if img_url and img_url.startswith('http') and 'bing.com' not in img_url:
                    try:
                        img_response = self.session.get(img_url, timeout=10)
                        img_response.raise_for_status()
                        
                        # Validate it's actually an image
                        if len(img_response.content) < 1000:  # Too small
                            continue
                            
                        # Determine file extension
                        content_type = img_response.headers.get('content-type', '')
                        if 'jpeg' in content_type or 'jpg' in content_type:
                            ext = '.jpg'
                        elif 'png' in content_type:
                            ext = '.png'
                        elif 'gif' in content_type:
                            ext = '.gif'
                        else:
                            ext = '.jpg'  # Default
                        
                        filename = f"image_{len(files):03d}{ext}"
                        filepath = os.path.join(temp_subdir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
                        
                        # Validate the image can be opened
                        try:
                            with Image.open(filepath) as test_img:
                                if test_img.size[0] > 100 and test_img.size[1] > 100:  # Reasonable size
                                    files.append(filepath)
                        except Exception:
                            os.remove(filepath)  # Remove invalid image
                            continue
                        
                        # Rate limiting
                        time.sleep(random.uniform(1, 2))
                        
                    except Exception as e:
                        logger.warning(f"Failed to download image {i}: {str(e)}")
                        continue
            
            return files
            
        except ImportError:
            logger.warning("BeautifulSoup not installed, skipping requests fallback")
            return []
        except Exception as e:
            logger.error(f"Requests fallback failed: {str(e)}")
            return []
    
    def cleanup(self):
        """Cleanup temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

class ImageManager:
    """Manages image search, AI evaluation, and processing for presentations"""
    
    def __init__(self, file_manager=None):
        """Initialize the image manager"""
        # Initialize Gemini for image evaluation
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self.evaluation_model = "gemini-2.5-flash"
        else:
            logger.warning("GEMINI_API_KEY not found - image evaluation will be disabled")
            self.client = None
        
        # Image directories will be created per session via file_manager
        
        self.file_manager = file_manager
        self.image_downloader = ImageDownloader()
    
    def _get_image_dir(self, session_id: str) -> Path:
        """Get image directory for a specific session"""
        if self.file_manager:
            subdirs = self.file_manager.get_session_subdirs(session_id)
            return subdirs['images']
        else:
            # Fallback to old structure if no file_manager
            image_dir = Path('data/images/processed')
            image_dir.mkdir(parents=True, exist_ok=True)
            return image_dir
    
    def process_all_images(self, 
                          slides_content: List[Dict[str, Any]],
                          progress_callback: Optional[Callable[[float], None]] = None) -> List[Dict[str, Any]]:
        """
        Process images for all slides in the presentation
        
        Args:
            slides_content: List of slide content with image specifications
            progress_callback: Optional callback for progress updates
            
        Returns:
            Updated slides content with processed image paths
        """
        try:
            # Collect all image requirements
            total_images = sum(len(slide.get('images', [])) for slide in slides_content)
            processed_images = 0
            
            logger.info(f"Processing {total_images} images across {len(slides_content)} slides")
            
            # Group images by slide for batch processing
            images_to_process = []
            for i, slide in enumerate(slides_content):
                for j, img_spec in enumerate(slide.get('images', [])):
                    images_to_process.append({
                        'slide_index': i,
                        'image_index': j,
                        'spec': img_spec,
                        'session_id': slide.get('session_id', 'unknown_session'),
                        'slide_content': slide  # Include full slide content for AI evaluation
                    })
            
            total_images = len(images_to_process)
            if total_images == 0:
                return slides_content
            
            # Process images for each slide
            for slide_idx, image_data in enumerate(images_to_process):
                try:
                    # Process individual image
                    processed_image = self._process_image_spec(image_data)
                    
                    # Update slide with processed image
                    slide = slides_content[image_data['slide_index']]
                    slide['images'][image_data['image_index']] = processed_image
                    
                    processed_images += 1
                    
                    # Update progress
                    if progress_callback:
                        progress = (processed_images / total_images) * 100
                        progress_callback(progress)
                        
                except Exception as e:
                    logger.error(f"Error processing image {image_data['image_index']+1} for slide {image_data['slide_index']+1}: {str(e)}")
                    # Add placeholder image
                    slide['images'][image_data['image_index']] = {
                        **image_data['spec'],
                        'file_path': None,
                        'status': 'failed',
                        'error': str(e)
                    }
            
            return slides_content
            
        except Exception as e:
            logger.error(f"Error processing images: {str(e)}")
            return slides_content # Return original content on error
        finally:
            # Cleanup temporary files
            self.image_downloader.cleanup()
    
    def _process_image_spec(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single image specification following the correct workflow"""
        image_spec = image_data['spec']
        description = image_spec.get('description', '')
        session_id = image_data.get('session_id', 'unknown_session')
        slide_content = image_data.get('slide_content', {})
        
        try:
            # Step 1: Search for images using the image search system
            search_results = self.image_downloader.download_images_for_evaluation(description, image_count=5)
            
            if search_results:
                logger.info(f"Found {len(search_results)} images for evaluation")
                
                # Step 2: Use Gemini-2.5-Flash to evaluate and select the best image
                selected_result = self._evaluate_and_select_image(search_results, image_spec, slide_content, session_id)
                
                if selected_result:
                    if selected_result.startswith("ENHANCED_DESCRIPTION:"):
                        # AI provided enhanced description for generation
                        enhanced_description = selected_result[len("ENHANCED_DESCRIPTION:"):]
                        logger.info(f"Using AI-enhanced description for generation: '{enhanced_description[:100]}...'")
                        return self._generate_image_with_description(image_data, enhanced_description)
                    else:
                        # AI selected an existing image
                        logger.info(f"AI selected suitable image: {selected_result}")
                        return self._download_and_process_selected(selected_result, image_data)
            
            # Step 3: If no suitable image found, generate one as fallback
            logger.info(f"No suitable image found, generating one for: '{description}'")
            return self._generate_image(image_data)
            
        except Exception as e:
            logger.error(f"Error processing image for '{description}': {str(e)}")
            return self._create_placeholder_image(image_data)

    def _evaluate_and_select_image(self, image_paths: List[str], image_spec: Dict[str, Any], slide_content: Dict[str, Any], session_id: str) -> Optional[str]:
        """Use Gemini-2.5-Flash to evaluate images and select the best one"""
        if not self.client:
            logger.warning("Gemini client not available for image evaluation")
            return image_paths[0] if image_paths else None
            
        try:
            start_time = time.time()
            
            # Prepare slide context for AI evaluation
            slide_title = slide_content.get('title', 'Untitled Slide')
            slide_transcript = slide_content.get('transcript', '')[:500]  # Limit length
            image_description = image_spec.get('description', '')
            
            # Create evaluation prompt
            prompt = f"""You are evaluating images for an educational presentation slide.

SLIDE CONTEXT:
- Title: {slide_title}
- Content: {slide_transcript}
- Required Image: {image_description}

I will show you {len(image_paths)} images. Evaluate each image based on:
1. Relevance to the slide content and required description
2. Educational appropriateness and quality
3. Visual clarity and professional appearance
4. Suitability for a university-level presentation

RESPONSE FORMAT:
- If ANY image is suitable, respond with ONLY the number of the best image (1, 2, 3, etc.).
- If NO images are suitable, provide an enhanced description for AI image generation that would be perfect for this slide. Make it detailed, specific, and optimized for image generation.

Images to evaluate:"""

            # Load images as PIL Image objects (correct format for Gemini API)
            pil_images = []
            for i, img_path in enumerate(image_paths):
                try:
                    with Image.open(img_path) as img:
                        # Convert to RGB if necessary
                        if img.mode not in ('RGB', 'RGBA'):
                            img = img.convert('RGB')
                        pil_images.append(img.copy())
                    prompt += f"\n\nImage {i+1}: [Image attached]"
                except Exception as e:
                    logger.warning(f"Failed to load image {img_path}: {e}")
                    continue
            
            if not pil_images:
                return None
                
            # Generate evaluation using correct Gemini API format
            contents = [prompt] + pil_images
            
            response = self.client.models.generate_content(
                model=f"models/{self.evaluation_model}",
                contents=contents
            )
            
            processing_time = time.time() - start_time
            
            # Log the interaction
            if self.file_manager:
                request_data = {
                    'prompt': prompt,
                    'image_count': len(pil_images),
                    'slide_title': slide_title,
                    'image_description': image_description
                }
                self.file_manager.save_ai_interaction_log(
                    session_id, 'image_evaluation', self.evaluation_model, 
                    request_data, response, processing_time, 
                    getattr(response, 'usage_metadata', None)
                )
            
            # Parse response
            evaluation_result = response.text.strip()
            logger.info(f"AI evaluation result: '{evaluation_result[:100]}...'")
            
            # Try to parse as a selected image number first
            try:
                selected_index = int(evaluation_result) - 1  # Convert to 0-based index
                if 0 <= selected_index < len(image_paths):
                    logger.info(f"AI selected image {selected_index + 1}")
                    return image_paths[selected_index]
                else:
                    logger.warning(f"AI selected invalid image index: {selected_index + 1}")
                    return None
            except ValueError:
                # If not a number, treat as enhanced description for generation
                if len(evaluation_result) > 10:  # Reasonable description length
                    logger.info("AI provided enhanced description for generation")
                    return f"ENHANCED_DESCRIPTION:{evaluation_result}"
                else:
                    logger.warning(f"AI returned unexpected response: '{evaluation_result}'")
                    return None
                
        except Exception as e:
            logger.error(f"Error in AI image evaluation: {str(e)}")
            return None

    def _download_and_process_selected(self, selected_image_path: str, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the AI-selected image"""
        try:
            # Get session image directory
            session_id = image_data.get('session_id', 'unknown_session')
            image_dir = self._get_image_dir(session_id)
            
            slide_num = image_data['slide_index'] + 1
            img_num = image_data['image_index'] + 1
            
            # Determine file extension
            _, ext = os.path.splitext(selected_image_path)
            if not ext:
                ext = '.png'
            
            filename = f"slide_{slide_num:02d}_img_{img_num:02d}{ext}"
            output_path = image_dir / filename
            
            # Copy and process the image
            shutil.copy2(selected_image_path, output_path)
            
            # Optimize the image
            with Image.open(output_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                
                # Resize if too large
                max_size = (1920, 1080)
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save optimized image
                img.save(output_path, optimize=True, quality=85)
            
            logger.info(f"Processed and saved AI-selected image to {output_path}")
            
            return {
                **image_data['spec'],
                'file_path': str(output_path),
                'status': 'success',
                'source': 'search_selected'
            }
            
        except Exception as e:
            logger.error(f"Error processing selected image: {str(e)}")
            return self._create_placeholder_image(image_data)

    def _generate_image_with_description(self, image_data: Dict[str, Any], enhanced_description: str) -> Dict[str, Any]:
        """Generate image using AI-enhanced description"""
        return self._generate_image_internal(image_data, enhanced_description)
    
    def _generate_image(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using Pollinations AI as fallback"""
        prompt = image_data['spec'].get('description', '')
        # Enhanced prompt for better generation
        enhanced_prompt = f"High-quality educational illustration: {prompt}. Professional, clean, suitable for academic presentation."
        return self._generate_image_internal(image_data, enhanced_prompt)
    
    def _generate_image_internal(self, image_data: Dict[str, Any], generation_prompt: str) -> Dict[str, Any]:
        """Internal method to generate image using Pollinations AI"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Use Pollinations API correctly
                encoded_prompt = urllib.parse.quote(generation_prompt)
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                params = {
                    "width": 1024,
                    "height": 768,
                    "nologo": "true",
                    "model": "flux",
                    "private": "true"
                }
                
                response = requests.get(url, params=params, timeout=300)
                response.raise_for_status()
                
                # Save generated image
                session_id = image_data.get('session_id', 'unknown_session')
                image_dir = self._get_image_dir(session_id)
                
                slide_num = image_data['slide_index'] + 1
                img_num = image_data['image_index'] + 1
                filename = f"slide_{slide_num:02d}_img_{img_num:02d}.png"
                output_path = image_dir / filename
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                # Validate the generated image
                with Image.open(output_path) as img:
                    if img.size[0] > 100 and img.size[1] > 100:
                        logger.info(f"Processed and saved image to {output_path}")
                        return {
                            **image_data['spec'],
                            'file_path': str(output_path),
                            'status': 'success',
                            'source': 'generated'
                        }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5 + random.randint(2, 8)
                    logger.warning(f"Generation attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to generate image after {max_retries} attempts: {e}")
        
        # If generation fails, create placeholder
        return self._create_placeholder_image(image_data)

    def _create_placeholder_image(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a placeholder image when search and generation fail"""
        try:
            description = image_data['spec'].get('description', 'Image')
            session_id = image_data.get('session_id', 'unknown_session')
            image_dir = self._get_image_dir(session_id)
            
            slide_num = image_data['slide_index'] + 1
            img_num = image_data['image_index'] + 1
            
            # Create a simple placeholder
            img = Image.new('RGB', (800, 600), color='lightgray')
            
            filename = f"slide_{slide_num:02d}_img_{img_num:02d}_placeholder.png"
            output_path = image_dir / filename
            img.save(output_path)
            
            logger.warning(f"Created placeholder image for: {description}")
            
            return {
                **image_data['spec'],
                'file_path': str(output_path),
                'status': 'placeholder',
                'source': 'placeholder'
            }
            
        except Exception as e:
            logger.error(f"Error creating placeholder: {str(e)}")
            return {
                **image_data['spec'],
                'file_path': None,
                'status': 'failed',
                'error': str(e)
            }

    def get_processing_summary(self, slides_content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of image processing results"""
        total_images = 0
        successful_images = 0
        generated_images = 0
        failed_images = 0
        
        for slide in slides_content:
            for img in slide.get('images', []):
                total_images += 1
                status = img.get('status', 'unknown')
                if status == 'success':
                    successful_images += 1
                    if img.get('source') == 'generated':
                        generated_images += 1
                elif status == 'failed':
                    failed_images += 1
        
        return {
            'total_images': total_images,
            'successful_images': successful_images,
            'generated_images': generated_images,
            'failed_images': failed_images,
            'success_rate': (successful_images / total_images * 100) if total_images > 0 else 0
        }

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        self.image_downloader.cleanup()