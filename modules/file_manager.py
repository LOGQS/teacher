#!/usr/bin/env python3
"""
File Manager - Data Persistence and Management
Handles saving, loading, and managing all generated content and user data.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import zipfile
import shutil

logger = logging.getLogger(__name__)

class FileManager:
    """Manages file operations and data persistence"""
    
    def __init__(self):
        """Initialize the file manager with session-based organization"""
        self.base_dir = Path('data')
        self.base_dir.mkdir(exist_ok=True)
        
        # Create main directories with new session-based structure
        self.dirs = {
            'sessions': self.base_dir / 'sessions',
            'exports': self.base_dir / 'exports',
            'temp': self.base_dir / 'temp'
        }
        
        # Create global directories
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize session index (replaces metadata index)
        self.session_index = self._load_session_index()
        
        # Clear old temporary files on startup
        self._cleanup_temp_files()
    
    def get_session_dir(self, session_id: str) -> Path:
        """Get the directory path for a specific session"""
        session_dir = self.dirs['sessions'] / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def get_session_subdirs(self, session_id: str) -> Dict[str, Path]:
        """Get all subdirectory paths for a session"""
        session_dir = self.get_session_dir(session_id)
        
        subdirs = {
            'audio': session_dir / 'audio',
            'images': session_dir / 'images', 
            'transcripts': session_dir / 'transcripts',
            'logs': session_dir / 'logs'
        }
        
        # Create subdirectories
        for dir_path in subdirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            
        return subdirs
    
    def _cleanup_temp_files(self):
        """Clean up old temporary files on startup"""
        try:
            temp_dir = self.dirs['temp']
            if temp_dir.exists():
                for item in temp_dir.iterdir():
                    try:
                        if item.is_file():
                            # Remove files older than 24 hours
                            import time
                            if time.time() - item.stat().st_mtime > 86400:  # 24 hours
                                item.unlink()
                        elif item.is_dir():
                            # Remove empty directories
                            try:
                                item.rmdir()
                            except OSError:
                                pass  # Directory not empty
                    except Exception as e:
                        logger.warning(f"Error cleaning temp file {item}: {e}")
                logger.info("Cleaned up old temporary files")
        except Exception as e:
            logger.error(f"Error cleaning temporary files: {str(e)}")
    
    def save_course_session(self, 
                          session_id: str,
                          course_data: Dict[str, Any],
                          presentation_path: Optional[str] = None,
                          audio_files: Optional[List[str]] = None) -> str:
        """
        Save a complete course session
        
        Args:
            session_id: Unique session identifier
            course_data: Complete course data including structure, slides, etc.
            presentation_path: Path to generated presentation file
            audio_files: List of audio file paths
            
        Returns:
            Session metadata file path
        """
        try:
            timestamp = datetime.now().isoformat()
            
            course_structure = course_data.get('course_structure', {})
            course_metadata = course_structure.get('metadata', {})
            
            # Create session metadata
            metadata = {
                'session_id': session_id,
                'created_at': timestamp,
                'course_title': course_structure.get('course_title', 'Untitled Course'),
                'topic': course_metadata.get('topic', ''),
                'complexity': course_metadata.get('complexity', 'intermediate'),
                'duration': course_structure.get('total_estimated_time', 'N/A'),
                'slide_count': len(course_data.get('slides_content', [])),
                'presentation_path': presentation_path,
                'audio_files': audio_files or [],
                'status': 'completed',
                'customizations': course_metadata.get('customizations', {}),
                'file_size': 0,
                'tags': self._generate_tags(course_data)
            }
            
            # Get session directory
            session_dir = self.get_session_dir(session_id)
            
            # Save main course data
            course_file = session_dir / "course.json"
            with open(course_file, 'w') as f:
                json.dump(course_data, f, indent=2)
            
            # Save metadata
            metadata_file = session_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Calculate total file size
            total_size = self._calculate_session_size(session_id, presentation_path, audio_files)
            metadata['file_size'] = total_size
            
            # Update metadata with file size
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update session index
            self.session_index[session_id] = metadata
            self._save_session_index()
            
            logger.info(f"Saved course session: {session_id}")
            return str(metadata_file)
            
        except Exception as e:
            logger.error(f"Error saving course session: {str(e)}")
            raise
    
    def load_course_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a course session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Course data dictionary or None if not found
        """
        try:
            session_dir = self.get_session_dir(session_id)
            course_file = session_dir / "course.json"
            
            if course_file.exists():
                with open(course_file, 'r') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading course session: {str(e)}")
            return None
    
    def get_course_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a course session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Metadata dictionary or None if not found
        """
        return self.session_index.get(session_id)
    
    def list_courses(self, 
                    sort_by: str = 'created_at',
                    filter_by: Optional[Dict[str, Any]] = None,
                    limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all saved courses
        
        Args:
            sort_by: Sort criteria ('created_at', 'title', 'topic', 'size')
            filter_by: Filter criteria dictionary
            limit: Maximum number of results
            
        Returns:
            List of course metadata dictionaries
        """
        try:
            courses = list(self.session_index.values())
            
            # Apply filters
            if filter_by:
                courses = self._filter_courses(courses, filter_by)
            
            # Sort courses
            if sort_by == 'created_at':
                courses.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            elif sort_by == 'title':
                courses.sort(key=lambda x: x.get('course_title', '').lower())
            elif sort_by == 'topic':
                courses.sort(key=lambda x: x.get('topic', '').lower())
            elif sort_by == 'size':
                courses.sort(key=lambda x: x.get('file_size', 0), reverse=True)
            
            # Apply limit
            if limit:
                courses = courses[:limit]
            
            return courses
            
        except Exception as e:
            logger.error(f"Error listing courses: {str(e)}")
            return []
    
    def delete_course_session(self, session_id: str) -> bool:
        """
        Delete a course session and all associated files
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deletion was successful
        """
        try:
            # Check if session exists
            if session_id not in self.session_index:
                logger.warning(f"No session found: {session_id}")
                return False
            
            # Get session directory
            session_dir = self.dirs['sessions'] / session_id
            
            # Delete entire session directory and all contents
            if session_dir.exists():
                shutil.rmtree(session_dir)
                logger.info(f"Deleted session directory: {session_dir}")
            
            # Remove from session index
            if session_id in self.session_index:
                del self.session_index[session_id]
                self._save_session_index()
            
            logger.info(f"Deleted course session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting course session: {str(e)}")
            return False
    
    def export_course_session(self, 
                            session_id: str,
                            export_format: str = 'zip',
                            include_audio: bool = True) -> Optional[str]:
        """
        Export a course session in specified format
        
        Args:
            session_id: Session identifier
            export_format: Export format ('zip', 'json')
            include_audio: Whether to include audio files
            
        Returns:
            Path to exported file or None if failed
        """
        try:
            metadata = self.get_course_metadata(session_id)
            if not metadata:
                logger.error(f"No metadata found for session: {session_id}")
                return None
            
            course_data = self.load_course_session(session_id)
            if not course_data:
                logger.error(f"No course data found for session: {session_id}")
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            course_title = metadata.get('course_title', 'course').replace(' ', '_')
            
            if export_format == 'zip':
                # Create ZIP export
                export_file = self.dirs['exports'] / f"{course_title}_{timestamp}.zip"
                
                with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add course data
                    zipf.writestr('course_data.json', json.dumps(course_data, indent=2))
                    zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
                    
                    # Add presentation file
                    presentation_path = metadata.get('presentation_path')
                    if presentation_path and Path(presentation_path).exists():
                        zipf.write(presentation_path, Path(presentation_path).name)
                    
                    # Add audio files if requested
                    if include_audio:
                        audio_files = metadata.get('audio_files', [])
                        for i, audio_file in enumerate(audio_files):
                            if audio_file and Path(audio_file).exists():
                                zipf.write(audio_file, f"audio/slide_{i+1}.wav")
                
                logger.info(f"Exported course session to ZIP: {export_file}")
                return str(export_file)
                
            elif export_format == 'json':
                # Create JSON export
                export_file = self.dirs['exports'] / f"{course_title}_{timestamp}.json"
                
                export_data = {
                    'metadata': metadata,
                    'course_data': course_data,
                    'exported_at': datetime.now().isoformat()
                }
                
                with open(export_file, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                logger.info(f"Exported course session to JSON: {export_file}")
                return str(export_file)
            
            else:
                logger.error(f"Unsupported export format: {export_format}")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting course session: {str(e)}")
            return None
    
    def import_course_session(self, import_file: str) -> Optional[str]:
        """
        Import a course session from file
        
        Args:
            import_file: Path to import file
            
        Returns:
            Session ID of imported course or None if failed
        """
        try:
            import_path = Path(import_file)
            
            if not import_path.exists():
                logger.error(f"Import file not found: {import_file}")
                return None
            
            if import_path.suffix.lower() == '.zip':
                # Import from ZIP
                with zipfile.ZipFile(import_file, 'r') as zipf:
                    # Extract course data
                    course_data = json.loads(zipf.read('course_data.json'))
                    metadata = json.loads(zipf.read('metadata.json'))
                    
                    # Generate new session ID
                    session_id = f"imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    # Update metadata
                    metadata['session_id'] = session_id
                    metadata['imported_at'] = datetime.now().isoformat()
                    
                    # Save course data
                    course_file = self.dirs['courses'] / f"{session_id}.json"
                    with open(course_file, 'w') as f:
                        json.dump(course_data, f, indent=2)
                    
                    # Save metadata
                    metadata_file = self.dirs['metadata'] / f"{session_id}_metadata.json"
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    
                    # Extract presentation file if exists
                    try:
                        presentation_data = zipf.read(zipf.namelist()[0])  # First .pptx file
                        presentation_file = self.dirs['presentations'] / f"{session_id}.pptx"
                        with open(presentation_file, 'wb') as f:
                            f.write(presentation_data)
                        metadata['presentation_path'] = str(presentation_file)
                    except:
                        pass
                    
                    # Update metadata index
                    self.metadata_index[session_id] = metadata
                    self._save_metadata_index()
                    
                    logger.info(f"Imported course session: {session_id}")
                    return session_id
                    
            elif import_path.suffix.lower() == '.json':
                # Import from JSON
                with open(import_file, 'r') as f:
                    import_data = json.load(f)
                
                course_data = import_data.get('course_data', {})
                metadata = import_data.get('metadata', {})
                
                # Generate new session ID
                session_id = f"imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Update metadata
                metadata['session_id'] = session_id
                metadata['imported_at'] = datetime.now().isoformat()
                
                # Save course data
                course_file = self.dirs['courses'] / f"{session_id}.json"
                with open(course_file, 'w') as f:
                    json.dump(course_data, f, indent=2)
                
                # Save metadata
                metadata_file = self.dirs['metadata'] / f"{session_id}_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                # Update metadata index
                self.metadata_index[session_id] = metadata
                self._save_metadata_index()
                
                logger.info(f"Imported course session: {session_id}")
                return session_id
            
            else:
                logger.error(f"Unsupported import format: {import_path.suffix}")
                return None
                
        except Exception as e:
            logger.error(f"Error importing course session: {str(e)}")
            return None
    
    def cleanup_old_files(self, max_age_days: int = 30):
        """
        Clean up old files
        
        Args:
            max_age_days: Maximum age of files to keep
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            removed_count = 0
            
            # Clean up temporary files
            for file_path in self.dirs['temp'].glob('*'):
                if file_path.is_file():
                    file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age < cutoff_date:
                        file_path.unlink()
                        removed_count += 1
            
            # Clean up old audio files (orphaned)
            audio_files_in_use = set()
            for metadata in self.metadata_index.values():
                audio_files_in_use.update(metadata.get('audio_files', []))
            
            for audio_file in self.dirs['audio'].glob('*.wav'):
                if str(audio_file) not in audio_files_in_use:
                    file_age = datetime.fromtimestamp(audio_file.stat().st_mtime)
                    if file_age < cutoff_date:
                        audio_file.unlink()
                        removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old files")
                
        except Exception as e:
            logger.warning(f"Error cleaning up old files: {str(e)}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            stats = {
                'total_courses': len(self.metadata_index),
                'total_size': 0,
                'directories': {}
            }
            
            for dir_name, dir_path in self.dirs.items():
                dir_size = 0
                file_count = 0
                
                for file_path in dir_path.rglob('*'):
                    if file_path.is_file():
                        dir_size += file_path.stat().st_size
                        file_count += 1
                
                stats['directories'][dir_name] = {
                    'size': dir_size,
                    'file_count': file_count
                }
                stats['total_size'] += dir_size
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {'error': str(e)}
    
    def _load_session_index(self) -> Dict[str, Any]:
        """Load session index from file"""
        try:
            index_file = self.base_dir / 'index.json'
            
            if index_file.exists():
                with open(index_file, 'r') as f:
                    return json.load(f)
            
            return {}
            
        except Exception as e:
            logger.warning(f"Error loading session index: {str(e)}")
            return {}
    
    def _save_session_index(self):
        """Save session index to file"""
        try:
            index_file = self.base_dir / 'index.json'
            
            with open(index_file, 'w') as f:
                json.dump(self.session_index, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving session index: {str(e)}")
    
    def _filter_courses(self, courses: List[Dict[str, Any]], filter_by: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter courses based on criteria"""
        filtered = []
        
        for course in courses:
            match = True
            
            # Check each filter criterion
            for key, value in filter_by.items():
                if key == 'topic' and value.lower() not in course.get('topic', '').lower():
                    match = False
                    break
                elif key == 'complexity' and course.get('complexity') != value:
                    match = False
                    break
                elif key == 'tags' and not any(tag in course.get('tags', []) for tag in value):
                    match = False
                    break
                elif key == 'date_range':
                    try:
                        course_date = datetime.fromisoformat(course.get('created_at', ''))
                        start_date = datetime.fromisoformat(value['start'])
                        end_date = datetime.fromisoformat(value['end'])
                        
                        if not (start_date <= course_date <= end_date):
                            match = False
                            break
                    except (ValueError, TypeError):
                        match = False
                        break
            
            if match:
                filtered.append(course)
        
        return filtered
    
    def _generate_tags(self, course_data: Dict[str, Any]) -> List[str]:
        """Generate tags for a course"""
        tags = []
        
        # Add topic-based tags
        topic = course_data.get('topic', '').lower()
        if 'programming' in topic or 'coding' in topic:
            tags.append('programming')
        if 'machine learning' in topic or 'ai' in topic:
            tags.append('ai')
        if 'data' in topic:
            tags.append('data-science')
        if 'web' in topic:
            tags.append('web-development')
        if 'design' in topic:
            tags.append('design')
        if 'business' in topic:
            tags.append('business')
        
        # Add complexity tag
        complexity = course_data.get('complexity', 'intermediate')
        tags.append(f'level-{complexity}')
        
        # Add slide count tag
        slide_count = len(course_data.get('slides_content', []))
        if slide_count < 10:
            tags.append('short')
        elif slide_count < 30:
            tags.append('medium')
        else:
            tags.append('long')
        
        return tags
    
    def _calculate_session_size(self, 
                              session_id: str,
                              presentation_path: Optional[str] = None,
                              audio_files: Optional[List[str]] = None) -> int:
        """Calculate total size of a session"""
        total_size = 0
        
        try:
            # Course data file
            course_file = self.dirs['courses'] / f"{session_id}.json"
            if course_file.exists():
                total_size += course_file.stat().st_size
            
            # Metadata file
            metadata_file = self.dirs['metadata'] / f"{session_id}_metadata.json"
            if metadata_file.exists():
                total_size += metadata_file.stat().st_size
            
            # Presentation file
            if presentation_path and Path(presentation_path).exists():
                total_size += Path(presentation_path).stat().st_size
            
            # Audio files
            if audio_files:
                for audio_file in audio_files:
                    if audio_file and Path(audio_file).exists():
                        total_size += Path(audio_file).stat().st_size
            
        except Exception as e:
            logger.warning(f"Error calculating session size: {str(e)}")
        
        return total_size
    
    def save_presentation(self, presentation_file: str, audio_files: List[str], course_structure: Dict[str, Any], presentation_plan: Dict[str, Any], slides_content: List[Dict[str, Any]], original_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save presentation data and return final data structure
        
        Args:
            presentation_file: Path to generated presentation file
            audio_files: List of audio file paths
            course_structure: Course structure data
            presentation_plan: Presentation plan data
            slides_content: Detailed slide content with full transcripts
            original_data: Original generation request data
            
        Returns:
            Final data structure with all relevant information
        """
        try:
            session_id = original_data.get('session_id', str(int(datetime.now().timestamp())))
            
            # Save individual transcripts for each slide using the full slides_content
            transcript_files = self.save_transcripts(session_id, slides_content)
            
            # Combine all data
            final_data = {
                'session_id': session_id,
                'course_structure': course_structure,
                'presentation_plan': presentation_plan,
                'slides_content': slides_content,
                'presentation_file': presentation_file,
                'audio_files': audio_files,
                'transcript_files': transcript_files,
                'metadata': {
                    'topic': original_data.get('topic'),
                    'complexity': original_data.get('complexity'),
                    'duration': original_data.get('duration'),
                    'learning_style': original_data.get('learningStyle') or original_data.get('learning_style'),
                    'created_at': datetime.now().isoformat(),
                    'customizations': original_data.get('customizations', {}),
                    'total_slides': len(slides_content),
                    'total_audio_files': len([f for f in audio_files if f]),
                    'total_transcript_files': len(transcript_files)
                }
            }
            
            # Save the complete session
            self.save_course_session(session_id, final_data, presentation_file, audio_files)
            
            return final_data
            
        except Exception as e:
            logger.error(f"Error saving presentation: {str(e)}")
            raise
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            File information dictionary
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {'error': 'File not found', 'exists': False}
            
            stat = path.stat()
            
            return {
                'exists': True,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'is_file': path.is_file(),
                'is_directory': path.is_dir(),
                'name': path.name,
                'extension': path.suffix
            }
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {'error': str(e), 'exists': False}
    
    def upload_file(self, file) -> Dict[str, Any]:
        """
        Upload a file to the system
        
        Args:
            file: File object from request
            
        Returns:
            Upload result information
        """
        try:
            if not file or file.filename == '':
                return {'error': 'No file provided'}
            
            # Generate safe filename
            import uuid
            safe_filename = f"{uuid.uuid4()}_{file.filename}"
            upload_path = self.dirs['temp'] / safe_filename
            
            # Save the file
            file.save(str(upload_path))
            
            # Get file info
            file_info = self.get_file_info(str(upload_path))
            
            return {
                'success': True,
                'filename': safe_filename,
                'original_filename': file.filename,
                'path': str(upload_path),
                'size': file_info.get('size', 0)
            }
            
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return {'error': str(e)}
    
    def import_course(self, file) -> Dict[str, Any]:
        """
        Import a course from uploaded file
        
        Args:
            file: File object containing course data
            
        Returns:
            Import result
        """
        try:
            # First upload the file
            upload_result = self.upload_file(file)
            
            if 'error' in upload_result:
                return upload_result
            
            file_path = upload_result['path']
            
            # Try to extract and import course data
            if file.filename.endswith('.zip'):
                # Handle ZIP file import
                return self._import_from_zip(file_path)
            elif file.filename.endswith('.json'):
                # Handle JSON file import
                return self._import_from_json(file_path)
            else:
                return {'error': 'Unsupported file format. Please use ZIP or JSON files.'}
                
        except Exception as e:
            logger.error(f"Error importing course: {str(e)}")
            return {'error': str(e)}
    
    def _import_from_zip(self, zip_path: str) -> Dict[str, Any]:
        """Import course from ZIP file"""
        try:
            # Placeholder implementation
            return {'error': 'ZIP import not yet implemented'}
        except Exception as e:
            return {'error': str(e)}
    
    def _import_from_json(self, json_path: str) -> Dict[str, Any]:
        """Import course from JSON file"""
        try:
            with open(json_path, 'r') as f:
                course_data = json.load(f)
            
            # Generate new session ID
            import uuid
            session_id = str(uuid.uuid4())
            
            # Save as new course session
            self.save_course_session(session_id, course_data)
            
            return {
                'success': True,
                'session_id': session_id,
                'message': 'Course imported successfully'
            }
            
        except Exception as e:
            return {'error': f'Failed to import JSON: {str(e)}'}
    
    def list_presentations(self) -> List[Dict[str, Any]]:
        """List all presentations (alias for list_courses)"""
        return self.list_courses()
    
    def get_presentation_path(self, presentation_id: str) -> Path:
        """Get path to presentation file"""
        # Try to find presentation file
        pptx_file = self.dirs['presentations'] / f"{presentation_id}.pptx"
        if pptx_file.exists():
            return pptx_file
        
        # Try course data file
        course_file = self.dirs['courses'] / f"{presentation_id}.json"
        if course_file.exists():
            return course_file
            
        # Return non-existent path
        return self.dirs['presentations'] / f"{presentation_id}.pptx"
    
    def get_presentation_metadata(self, presentation_id: str) -> Dict[str, Any]:
        """Get presentation metadata (alias for get_course_metadata)"""
        return self.get_course_metadata(presentation_id)
    
    def save_transcripts(self, session_id: str, slides_content: List[Dict[str, Any]]) -> List[str]:
        """
        Save individual transcript files for each slide
        
        Args:
            session_id: Session identifier
            slides_content: List of slide content dictionaries
            
        Returns:
            List of saved transcript file paths
        """
        try:
            # Get session subdirectories
            subdirs = self.get_session_subdirs(session_id)
            transcript_dir = subdirs['transcripts']
            
            transcript_paths = []
            for i, slide in enumerate(slides_content, 1):
                # Extract transcript content
                transcript_content = slide.get('transcript', '')
                
                if transcript_content:
                    transcript_file = transcript_dir / f"slide_{i:02d}.txt"
                    
                    try:
                        # Write only the raw transcript text to the file
                        with open(transcript_file, 'w', encoding='utf-8') as f:
                            f.write(transcript_content)
                        transcript_paths.append(str(transcript_file))
                    except Exception as e:
                        logger.error(f"Error saving transcript for slide {i}: {str(e)}")

            logger.info(f"Saved {len(transcript_paths)} transcripts to {transcript_dir}")
            return transcript_paths
            
        except Exception as e:
            logger.error(f"Error saving transcripts: {str(e)}")
            return []
    
    def save_ai_interaction_log(self, session_id: str, stage: str, model_name: str, request_data: Any, response_data: Any, processing_time: float, usage_metadata: Optional[Any] = None) -> str:
        """
        Save a log of a single AI model interaction to a file.
        Now handles complex objects by converting them to strings.
        """
        try:
            # Get session subdirectories
            subdirs = self.get_session_subdirs(session_id)
            log_dir = subdirs['logs']

            timestamp = datetime.now()
            log_filename = f"{timestamp.strftime('%Y%m%d_%H%M%S%f')}_{stage}.log"
            log_filepath = log_dir / log_filename
            
            # Prepare a safe representation of the response
            response_text = ""
            if hasattr(response_data, 'text'):
                response_text = response_data.text
            elif isinstance(response_data, (dict, list)):
                 # Fallback to json string if it's a dict/list
                try:
                    response_text = json.dumps(response_data, indent=2, default=str)
                except Exception:
                    response_text = str(response_data)
            else:
                response_text = str(response_data)

            usage_text = ""
            if usage_metadata:
                if hasattr(usage_metadata, 'total_token_count'):
                    usage_text = (
                        f"Prompt Tokens: {usage_metadata.prompt_token_count}, "
                        f"Candidates Tokens: {usage_metadata.candidates_token_count}, "
                        f"Total Tokens: {usage_metadata.total_token_count}"
                    )
                else:
                    usage_text = str(usage_metadata)

            log_content = f"""
Timestamp: {timestamp.isoformat()}
Session ID: {session_id}
Stage: {stage}
Model: {model_name}
Processing Time: {round(processing_time, 2)}s
Usage: {usage_text}
==================== REQUEST ====================
{json.dumps(request_data, indent=2, default=str)}
==================== RESPONSE ===================
{response_text}
"""
            with open(log_filepath, 'w', encoding='utf-8') as f:
                f.write(log_content.strip())
            
            logger.debug(f"Saved AI interaction log to {log_filepath}")
            return str(log_filepath)
            
        except Exception as e:
            logger.error(f"Error saving AI interaction log: {e}")
            # Log the problematic data for debugging
            logger.debug(f"Request Data: {str(request_data)}")
            logger.debug(f"Response Data: {str(response_data)}")
            logger.debug(f"Usage Metadata: {str(usage_metadata)}")
            return ""
    
    def get_session_logs(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all conversation logs for a given session.
        
        Args:
            session_id: The session identifier.
            
        Returns:
            A list of conversation logs for the session.
        """
        try:
            # Get session subdirectories
            subdirs = self.get_session_subdirs(session_id)
            log_dir = subdirs['logs']
            
            if not log_dir.exists():
                return []
            
            logs = []
            for log_file in sorted(log_dir.glob('*.json')):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)
                    logs.append(log_data)
                except Exception as e:
                    logger.warning(f"Error reading log file {log_file}: {str(e)}")
            
            return logs
            
        except Exception as e:
            logger.error(f"Error getting session logs: {str(e)}")
            return []