import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FiPlay, 
  FiDownload, 
  FiTrash2, 
  FiSearch, 
  FiFilter,
  FiCalendar,
  FiClock,
  FiLayers,
  FiMoreVertical,
  FiUpload,
  FiBookOpen
} from 'react-icons/fi'
import { useAppStore } from '../store/appStore'
import { courseAPI, downloadFile, uploadFile } from '../api/client'
import { toast } from 'react-hot-toast'

const LibraryPage = () => {
  const navigate = useNavigate()
  const { courses, setCourses, removeCourse } = useAppStore()
  
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [filterBy, setFilterBy] = useState('all')
  const [showDropdown, setShowDropdown] = useState(null)
  
  useEffect(() => {
    loadCourses()
  }, [])
  
  const loadCourses = async () => {
    try {
      setLoading(true)
      const response = await courseAPI.listCourses({ sort_by: sortBy })
      setCourses(response.data)
    } catch (error) {
      toast.error('Failed to load courses')
      console.error('Load courses error:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const handleDeleteCourse = async (sessionId) => {
    if (!confirm('Are you sure you want to delete this course? This action cannot be undone.')) {
      return
    }
    
    try {
      await courseAPI.deleteCourse(sessionId)
      removeCourse(sessionId)
      toast.success('Course deleted successfully')
    } catch (error) {
      toast.error('Failed to delete course')
      console.error('Delete course error:', error)
    }
  }
  
  const handleExportCourse = async (sessionId, courseTitle) => {
    try {
      const response = await courseAPI.exportCourse(sessionId, 'zip')
      const filename = `${courseTitle.replace(/[^a-zA-Z0-9]/g, '_')}.zip`
      downloadFile(response.data, filename)
      toast.success('Course exported successfully')
    } catch (error) {
      toast.error('Failed to export course')
      console.error('Export course error:', error)
    }
  }
  
  const handleImportCourse = async (file) => {
    try {
      const response = await courseAPI.importCourse(file)
      await loadCourses() // Reload courses list
      toast.success('Course imported successfully')
    } catch (error) {
      toast.error('Failed to import course')
      console.error('Import course error:', error)
    }
  }
  
  const filteredCourses = courses.filter(course => {
    const matchesSearch = course.course_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         course.topic.toLowerCase().includes(searchTerm.toLowerCase())
    
    if (filterBy === 'all') return matchesSearch
    if (filterBy === 'beginner') return matchesSearch && course.complexity === 'beginner'
    if (filterBy === 'intermediate') return matchesSearch && course.complexity === 'intermediate'
    if (filterBy === 'advanced') return matchesSearch && course.complexity === 'advanced'
    
    return matchesSearch
  })
  
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }
  
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="min-h-screen pt-20 pb-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8"
        >
          <div>
            <h1 className="text-3xl font-bold mb-2">Course Library</h1>
            <p className="text-dark-text-secondary">
              {courses.length} saved courses
            </p>
          </div>
          
          {/* Import Button */}
          <div className="flex items-center gap-4">
            <label className="btn-secondary cursor-pointer">
              <FiUpload className="w-4 h-4" />
              Import Course
              <input
                type="file"
                accept=".zip,.json"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files[0]
                  if (file) handleImportCourse(file)
                }}
              />
            </label>
          </div>
        </motion.div>

        {/* Search and Filters */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card p-6 mb-8"
        >
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-dark-text-secondary w-4 h-4" />
              <input
                type="text"
                placeholder="Search courses..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-field pl-10 w-full"
              />
            </div>
            
            {/* Filter by complexity */}
            <select
              value={filterBy}
              onChange={(e) => setFilterBy(e.target.value)}
              className="input-field"
            >
              <option value="all">All Levels</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
            
            {/* Sort by */}
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value)
                loadCourses()
              }}
              className="input-field"
            >
              <option value="created_at">Latest First</option>
              <option value="title">Title A-Z</option>
              <option value="topic">Topic A-Z</option>
              <option value="size">File Size</option>
            </select>
          </div>
        </motion.div>

        {/* Courses Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="loading-spinner w-8 h-8 border-ios-blue mx-auto mb-4" />
            <p className="text-dark-text-secondary">Loading courses...</p>
          </div>
        ) : filteredCourses.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-12"
          >
            <div className="w-16 h-16 bg-dark-card rounded-full flex items-center justify-center mx-auto mb-4">
              <FiBookOpen className="w-8 h-8 text-dark-text-secondary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No courses found</h3>
            <p className="text-dark-text-secondary mb-6">
              {searchTerm ? 'Try adjusting your search terms' : 'Start by creating your first course'}
            </p>
            <button
              onClick={() => navigate('/')}
              className="btn-primary"
            >
              Create Course
            </button>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <AnimatePresence>
              {filteredCourses.map((course, index) => (
                <motion.div
                  key={course.session_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ delay: index * 0.1 }}
                  className="card card-hover p-6 relative"
                >
                  {/* Course Header */}
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold mb-1 line-clamp-2">
                        {course.course_title}
                      </h3>
                      <p className="text-sm text-dark-text-secondary mb-2">
                        {course.topic}
                      </p>
                    </div>
                    
                    {/* Actions Dropdown */}
                    <div className="relative">
                      <button
                        onClick={() => setShowDropdown(showDropdown === course.session_id ? null : course.session_id)}
                        className="p-2 hover:bg-dark-border rounded-lg transition-colors"
                      >
                        <FiMoreVertical className="w-4 h-4" />
                      </button>
                      
                      <AnimatePresence>
                        {showDropdown === course.session_id && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="absolute right-0 top-full mt-2 bg-dark-card border border-dark-border rounded-xl shadow-lg z-10 min-w-40"
                          >
                            <button
                              onClick={() => {
                                handleExportCourse(course.session_id, course.course_title)
                                setShowDropdown(null)
                              }}
                              className="w-full text-left px-4 py-3 hover:bg-dark-border transition-colors flex items-center gap-2"
                            >
                              <FiDownload className="w-4 h-4" />
                              Export
                            </button>
                            <button
                              onClick={() => {
                                handleDeleteCourse(course.session_id)
                                setShowDropdown(null)
                              }}
                              className="w-full text-left px-4 py-3 hover:bg-dark-border transition-colors flex items-center gap-2 text-ios-destructive"
                            >
                              <FiTrash2 className="w-4 h-4" />
                              Delete
                            </button>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                  
                  {/* Course Metadata */}
                  <div className="space-y-3 mb-6">
                    <div className="flex items-center gap-2 text-sm text-dark-text-secondary">
                      <FiLayers className="w-4 h-4" />
                      <span className="capitalize">{course.complexity}</span>
                      <span>•</span>
                      <span>{course.slide_count} slides</span>
                    </div>
                    
                    <div className="flex items-center gap-2 text-sm text-dark-text-secondary">
                      <FiClock className="w-4 h-4" />
                      <span>{course.duration}</span>
                    </div>
                    
                    <div className="flex items-center gap-2 text-sm text-dark-text-secondary">
                      <FiCalendar className="w-4 h-4" />
                      <span>{formatDate(course.created_at)}</span>
                    </div>
                    
                    {course.file_size > 0 && (
                      <div className="text-xs text-dark-text-secondary">
                        Size: {formatFileSize(course.file_size)}
                      </div>
                    )}
                  </div>
                  
                  {/* Tags */}
                  {course.tags && course.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-4">
                      {course.tags.slice(0, 3).map((tag, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-ios-blue/10 text-ios-blue text-xs rounded-lg"
                        >
                          {tag}
                        </span>
                      ))}
                      {course.tags.length > 3 && (
                        <span className="px-2 py-1 bg-dark-border text-dark-text-secondary text-xs rounded-lg">
                          +{course.tags.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                  
                  {/* Play Button */}
                  <button
                    onClick={() => navigate(`/presentation/${course.session_id}`)}
                    className="btn-primary w-full flex items-center justify-center gap-2"
                  >
                    <FiPlay className="w-4 h-4" />
                    Start Learning
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
      
      {/* Click outside to close dropdown */}
      {showDropdown && (
        <div
          className="fixed inset-0 z-5"
          onClick={() => setShowDropdown(null)}
        />
      )}
    </div>
  )
}

export default LibraryPage