import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import SyllabusUpload from '../components/SyllabusUpload'
import ProgressTracker from '../components/ProgressTracker'
import { uploadSyllabus, startAnalysis, getStatus } from '../api/client'

function Home() {
  const [file, setFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const navigate = useNavigate()
  const pollRef = useRef(null)

  // Poll for status updates
  useEffect(() => {
    if (!jobId || !isAnalyzing) return

    const poll = async () => {
      try {
        const statusData = await getStatus(jobId)
        setStatus(statusData)

        if (statusData.status === 'completed') {
          setIsAnalyzing(false)
          clearInterval(pollRef.current)
          // Navigate to results
          setTimeout(() => navigate(`/results/${jobId}`), 1000)
        } else if (statusData.status === 'failed') {
          setIsAnalyzing(false)
          setError(statusData.error || 'Analysis failed')
          clearInterval(pollRef.current)
        }
      } catch (err) {
        console.error('Poll error:', err)
      }
    }

    pollRef.current = setInterval(poll, 2000)
    poll() // Immediate first check

    return () => clearInterval(pollRef.current)
  }, [jobId, isAnalyzing, navigate])

  const handleAnalyze = async () => {
    if (!file) return

    setError(null)
    setIsUploading(true)

    try {
      // Step 1: Upload the file
      const uploadResult = await uploadSyllabus(file)
      setIsUploading(false)

      // Step 2: Start analysis
      setIsAnalyzing(true)
      const analysisResult = await startAnalysis(uploadResult.file_path)
      setJobId(analysisResult.job_id)
    } catch (err) {
      setIsUploading(false)
      setIsAnalyzing(false)
      setError(err.response?.data?.detail || err.message || 'Something went wrong')
    }
  }

  return (
    <div>
      {/* Hero */}
      <section className="hero">
        <h1>Your AI Study Agent</h1>
        <p>
          Upload your exam syllabus — we'll find the best YouTube videos for every topic
          and generate study notes. Powered by AI. 100% free.
        </p>
      </section>

      {/* Upload Zone */}
      <SyllabusUpload onFileSelect={setFile} selectedFile={file} />

      {/* Analyze Button */}
      {!isAnalyzing && (
        <button
          className="btn btn-primary analyze-btn"
          onClick={handleAnalyze}
          disabled={!file || isUploading}
          id="analyze-btn"
        >
          {isUploading ? '📤 Uploading...' : '🚀 Analyze Syllabus'}
        </button>
      )}

      {/* Error */}
      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}

      {/* Progress */}
      {isAnalyzing && status && (
        <ProgressTracker
          messages={status.progress_messages || []}
          currentStep={status.current_step || ''}
          status={status.status || 'running'}
        />
      )}

      {/* Loading spinner while waiting for first status */}
      {isAnalyzing && !status && (
        <div className="spinner" />
      )}
    </div>
  )
}

export default Home
