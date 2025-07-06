#!/usr/bin/env python3
"""
Enhanced Progress Tracking System
Provides comprehensive progress tracking with stage-specific details, real-time statistics,
and detailed status messages for course generation.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class ProgressStage:
    """Represents a single progress stage"""
    stage_id: str
    name: str
    description: str
    weight: float  # Percentage of total progress (0-100)
    substages: List[str] = None
    current_substage: str = ""
    substage_progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.substages is None:
            self.substages = []
        if self.details is None:
            self.details = {}

@dataclass
class ProcessingStatistics:
    """Processing statistics and metrics"""
    total_topics: int = 0
    total_subtopics: int = 0
    total_slides: int = 0
    slides_generated: int = 0
    images_processed: int = 0
    total_images: int = 0
    audio_files_generated: int = 0
    total_audio_files: int = 0
    
    # Performance metrics
    avg_slides_per_minute: float = 0.0
    avg_images_per_minute: float = 0.0
    estimated_completion_time: Optional[str] = None
    processing_speed: str = "Calculating..."
    
    # AI model usage
    api_calls_made: int = 0
    total_tokens_used: int = 0
    avg_response_time: float = 0.0

class ProgressTracker:
    """Enhanced progress tracking with detailed stage management and statistics"""
    
    def __init__(self, session_id: str):
        """Initialize progress tracker for a session"""
        self.session_id = session_id
        self.start_time = time.time()
        self.last_update_time = time.time()
        
        # Define progress stages
        self.stages = [
            ProgressStage(
                stage_id="initialization",
                name="Initializing",
                description="Setting up course generation pipeline",
                weight=5.0,
                substages=["validation", "configuration", "setup"]
            ),
            ProgressStage(
                stage_id="course_structure",
                name="Generating Course Structure",
                description="Creating hierarchical course outline with AI",
                weight=15.0,
                substages=["topic_analysis", "structure_generation", "validation"]
            ),
            ProgressStage(
                stage_id="presentation_planning",
                name="Planning Presentation",
                description="Converting course structure to slide format",
                weight=10.0,
                substages=["format_conversion", "slide_planning", "optimization"]
            ),
            ProgressStage(
                stage_id="slide_generation",
                name="Generating Slide Content",
                description="Creating detailed content for each slide",
                weight=35.0,
                substages=["content_creation", "layout_design", "quality_check"]
            ),
            ProgressStage(
                stage_id="image_processing",
                name="Processing Images",
                description="Finding and generating images for slides",
                weight=20.0,
                substages=["image_search", "image_generation", "optimization"]
            ),
            ProgressStage(
                stage_id="presentation_building",
                name="Building Presentation",
                description="Assembling PowerPoint presentation",
                weight=8.0,
                substages=["slide_assembly", "formatting", "final_review"]
            ),
            ProgressStage(
                stage_id="audio_generation",
                name="Generating Audio",
                description="Creating TTS narration for slides",
                weight=5.0,
                substages=["text_processing", "speech_synthesis", "audio_optimization"]
            ),
            ProgressStage(
                stage_id="finalization",
                name="Finalizing",
                description="Saving files and creating metadata",
                weight=2.0,
                substages=["file_saving", "metadata_creation", "cleanup"]
            )
        ]
        
        self.current_stage_index = 0
        self.overall_progress = 0.0
        self.statistics = ProcessingStatistics()
        
        # Progress callbacks
        self.progress_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Detailed progress history
        self.progress_history = []
        
    def get_current_status(self) -> Dict[str, Any]:
        """Get current progress status"""
        current_stage = self.stages[self.current_stage_index] if self.current_stage_index < len(self.stages) else None
        
        elapsed_time = time.time() - self.start_time
        
        status = {
            'session_id': self.session_id,
            'overall_progress': round(self.overall_progress, 1),
            'current_stage': {
                'id': current_stage.stage_id if current_stage else 'completed',
                'name': current_stage.name if current_stage else 'Completed',
                'description': current_stage.description if current_stage else 'Course generation completed',
                'progress': round(current_stage.substage_progress, 1) if current_stage else 100.0,
                'current_substage': current_stage.current_substage if current_stage else '',
                'details': current_stage.details if current_stage else {}
            },
            'statistics': asdict(self.statistics),
            'timing': {
                'elapsed_time_seconds': round(elapsed_time, 1),
                'elapsed_time_formatted': self._format_duration(elapsed_time),
                'estimated_total_time': self._estimate_total_time(),
                'estimated_remaining': self._estimate_remaining_time()
            },
            'stages_summary': [
                {
                    'id': stage.stage_id,
                    'name': stage.name,
                    'completed': stage.end_time is not None,
                    'progress': 100.0 if stage.end_time else (stage.substage_progress if stage.start_time else 0.0)
                }
                for stage in self.stages
            ],
            'last_updated': datetime.now().isoformat()
        }
        
        return status
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _estimate_total_time(self) -> str:
        """Estimate total completion time"""
        if self.overall_progress > 5:
            elapsed = time.time() - self.start_time
            estimated_total = (elapsed / self.overall_progress) * 100
            return self._format_duration(estimated_total)
        return "Calculating..."
    
    def _estimate_remaining_time(self) -> str:
        """Estimate remaining time"""
        if self.overall_progress > 5:
            elapsed = time.time() - self.start_time
            estimated_total = (elapsed / self.overall_progress) * 100
            remaining = max(0, estimated_total - elapsed)
            return self._format_duration(remaining)
        return "Calculating..."
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback function to be called on progress updates"""
        self.progress_callbacks.append(callback)
    
    def start_stage(self, stage_id: str, details: Dict[str, Any] = None):
        """Start a specific stage"""
        # Find the stage by ID
        stage = next((s for s in self.stages if s.stage_id == stage_id), None)
        if not stage:
            logger.warning(f"Stage {stage_id} not found")
            return
        
        # Update current stage index
        self.current_stage_index = self.stages.index(stage)
        
        # Set stage start time and details
        stage.start_time = time.time()
        stage.substage_progress = 0.0
        stage.current_substage = stage.substages[0] if stage.substages else ""
        if stage.details is None:
            stage.details = {}
        if details:
            stage.details.update(details)
        
        # Emit progress update
        self._emit_progress_update()
    
    def complete_stage(self, stage_id: str):
        """Complete a specific stage"""
        stage = next((s for s in self.stages if s.stage_id == stage_id), None)
        if not stage:
            logger.warning(f"Stage {stage_id} not found")
            return
        
        # Set stage end time and completion
        stage.end_time = time.time()
        stage.substage_progress = 100.0
        stage.current_substage = ""
        
        # Update overall progress
        self._update_overall_progress()
        
        # Move to next stage
        if self.current_stage_index < len(self.stages) - 1:
            self.current_stage_index += 1
            next_stage = self.stages[self.current_stage_index]
            next_stage.start_time = time.time()
        
        # Emit progress update
        self._emit_progress_update()
    
    def update_stage(self, name: str, description: str) -> Dict[str, Any]:
        """Update the name and description of the current stage."""
        if self.current_stage_index < len(self.stages):
            stage = self.stages[self.current_stage_index]
            stage.name = name
            stage.description = description
            self._emit_progress_update()
            return self.get_current_status()
        else:
            logger.warning("Attempted to update stage when no stages are active.")
            return self.get_current_status()
    
    def update_statistics(self, **kwargs):
        """Update processing statistics"""
        for key, value in kwargs.items():
            if hasattr(self.statistics, key):
                setattr(self.statistics, key, value)
        
        # Update performance metrics
        self._update_performance_metrics()
        
        # Emit progress update
        self._emit_progress_update()
    
    def update_stage_progress(self, stage_id: str, progress: float, details: Dict[str, Any] = None):
        """Update progress within a specific stage"""
        stage = next((s for s in self.stages if s.stage_id == stage_id), None)
        if not stage:
            logger.warning(f"Stage {stage_id} not found")
            return
        
        # Update substage progress
        stage.substage_progress = min(100.0, max(0.0, progress))
        
        # Update details if provided
        if stage.details is None:
            stage.details = {}
        if details:
            stage.details.update(details)
        
        # Update overall progress
        self._update_overall_progress()
        
        # Emit progress update
        self._emit_progress_update()
    
    def export_progress_report(self) -> Dict[str, Any]:
        """Export a comprehensive progress report"""
        current_time = time.time()
        total_elapsed = current_time - self.start_time
        
        report = {
            'session_id': self.session_id,
            'total_elapsed_time': total_elapsed,
            'total_elapsed_formatted': self._format_duration(total_elapsed),
            'overall_progress': self.overall_progress,
            'stages': [
                {
                    'stage_id': stage.stage_id,
                    'name': stage.name,
                    'description': stage.description,
                    'weight': stage.weight,
                    'completed': stage.end_time is not None,
                    'time_spent': (stage.end_time - stage.start_time) if stage.start_time and stage.end_time else 0,
                    'details': stage.details
                }
                for stage in self.stages
            ],
            'statistics': asdict(self.statistics),
            'performance_summary': {
                'avg_slides_per_minute': self.statistics.avg_slides_per_minute,
                'avg_images_per_minute': self.statistics.avg_images_per_minute,
                'processing_efficiency': self._calculate_processing_efficiency()
            }
        }
        
        return report
    
    def _update_overall_progress(self):
        """Update overall progress based on stage completion"""
        total_progress = 0.0
        
        for stage in self.stages:
            if stage.end_time:
                # Stage is complete
                total_progress += stage.weight
            elif stage.start_time:
                # Stage is in progress
                stage_progress = (stage.substage_progress / 100.0) * stage.weight
                total_progress += stage_progress
        
        self.overall_progress = min(100.0, total_progress)
    
    def _update_performance_metrics(self):
        """Update performance metrics based on current statistics"""
        elapsed_time = time.time() - self.start_time
        elapsed_minutes = elapsed_time / 60.0
        
        if elapsed_minutes > 0:
            self.statistics.avg_slides_per_minute = self.statistics.slides_generated / elapsed_minutes
            self.statistics.avg_images_per_minute = self.statistics.images_processed / elapsed_minutes
        
        # Update processing speed indicator
        if self.statistics.slides_generated > 0:
            avg_time_per_slide = elapsed_time / self.statistics.slides_generated
            if avg_time_per_slide < 30:
                self.statistics.processing_speed = "Fast"
            elif avg_time_per_slide < 60:
                self.statistics.processing_speed = "Normal"
            else:
                self.statistics.processing_speed = "Slow"
        
        # Update estimated completion time
        if self.overall_progress > 5:
            estimated_total_time = (elapsed_time / self.overall_progress) * 100
            remaining_time = max(0, estimated_total_time - elapsed_time)
            self.statistics.estimated_completion_time = self._format_duration(remaining_time)
    
    def _calculate_processing_efficiency(self) -> float:
        """Calculate processing efficiency as a percentage"""
        if self.statistics.total_slides == 0:
            return 0.0
        
        # Base efficiency on slides completed vs time taken
        elapsed_minutes = (time.time() - self.start_time) / 60.0
        if elapsed_minutes == 0:
            return 100.0
        
        # Assume target of 2 slides per minute for full efficiency
        target_slides = elapsed_minutes * 2
        efficiency = (self.statistics.slides_generated / target_slides) * 100
        return min(100.0, efficiency)
    
    def _emit_progress_update(self):
        """Emit progress update to all registered callbacks"""
        try:
            status = self.get_current_status()
            for callback in self.progress_callbacks:
                callback(status)
        except Exception as e:
            logger.error(f"Error emitting progress update: {str(e)}")
    
    def add_progress_entry(self, entry: Dict[str, Any]):
        """Add a progress entry to the history"""
        entry['timestamp'] = datetime.now().isoformat()
        self.progress_history.append(entry)
        
        # Keep only last 100 entries to prevent memory issues
        if len(self.progress_history) > 100:
            self.progress_history = self.progress_history[-100:]
    
    def add_log_entry(self, level: str, message: str):
        """Add a log entry to the progress tracker"""
        log_entry = {
            'type': 'log',
            'level': level,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id
        }
        
        # Add to progress history
        self.add_progress_entry(log_entry)
        
        # Also log to Python logger
        if level == 'info':
            logger.info(f"[{self.session_id}] {message}")
        elif level == 'warning':
            logger.warning(f"[{self.session_id}] {message}")
        elif level == 'error':
            logger.error(f"[{self.session_id}] {message}")
        elif level == 'debug':
            logger.debug(f"[{self.session_id}] {message}")
        else:
            logger.info(f"[{self.session_id}] {message}")
    
    def _emit_enhanced_progress(self, socketio_instance, room):
        """Emit enhanced progress update via SocketIO"""
        status = self.get_current_status()
        
        # Emit enhanced progress event
        socketio_instance.emit('enhanced_progress', status, room=room)
        
        # Also emit legacy progress event for backward compatibility
        legacy_progress = {
            'progress': status['overall_progress'],
            'step': status['current_stage']['name'],
            'stage': status['current_stage']['id'],
            'details': status['current_stage']['description'],
            'estimated_time': status['timing']['estimated_remaining'],
            'statistics': status['statistics'],
            'timestamp': time.time()
        }
        
        socketio_instance.emit('course_progress', legacy_progress, room=room)