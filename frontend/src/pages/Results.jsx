import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import VideoCard from '../components/VideoCard'
import NotesViewer from '../components/NotesViewer'
import { getResults, getNotes } from '../api/client'

function Results() {
  const { jobId } = useParams()
  const [results, setResults] = useState(null)
  const [notes, setNotes] = useState(null)
  const [activeTab, setActiveTab] = useState('videos')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [resultsData, notesData] = await Promise.all([
          getResults(jobId),
          getNotes(jobId),
        ])
        setResults(resultsData)
        setNotes(notesData.study_notes)
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load results')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [jobId])

  if (loading) return <div className="spinner" />
  if (error) return <div className="error-message">❌ {error}</div>
  if (!results) return <div className="error-message">No results found</div>

  const recommendation = results.recommendation || {}
  const tier1Videos = results.tier1_videos || []
  const tier2Videos = results.tier2_videos || []
  const coverageReport = results.coverage_report || []
  const topics = results.topics || []
  const subject = results.syllabus_analysis?.subject || 'Your Syllabus'

  const formatWatchTime = (seconds) => {
    if (!seconds) return '0m'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    return h > 0 ? `${h}h ${m}m` : `${m}m`
  }

  return (
    <div>
      {/* Header */}
      <div className="results-header">
        <h1>📋 Analysis Complete</h1>
        <div className="subject">{subject}</div>
      </div>

      {/* Coverage Summary */}
      <div className="coverage-summary">
        <div className="coverage-stat">
          <div className="value">{recommendation.total_topics || 0}</div>
          <div className="label">Topics Found</div>
        </div>
        <div className="coverage-stat">
          <div className="value">
            {recommendation.coverage_percentage || 0}%
          </div>
          <div className="label">Coverage</div>
        </div>
        <div className="coverage-stat">
          <div className="value">{tier1Videos.length + tier2Videos.filter(v => v.video).length}</div>
          <div className="label">Videos</div>
        </div>
        <div className="coverage-stat">
          <div className="value">
            {formatWatchTime(recommendation.total_watch_time_seconds || 0)}
          </div>
          <div className="label">Watch Time</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tab-btn ${activeTab === 'videos' ? 'active' : ''}`}
          onClick={() => setActiveTab('videos')}
          id="tab-videos"
        >
          🎬 Videos
        </button>
        <button
          className={`tab-btn ${activeTab === 'notes' ? 'active' : ''}`}
          onClick={() => setActiveTab('notes')}
          id="tab-notes"
        >
          📝 Study Notes
        </button>
        <button
          className={`tab-btn ${activeTab === 'coverage' ? 'active' : ''}`}
          onClick={() => setActiveTab('coverage')}
          id="tab-coverage"
        >
          📊 Coverage Map
        </button>
      </div>

      {/* Videos Tab */}
      {activeTab === 'videos' && (
        <div>
          {/* Tier 1 */}
          {tier1Videos.length > 0 && (
            <div className="tier-section">
              <div className="tier-header">
                <span className="tier-badge tier1">TIER 1</span>
                Combo Videos — Watch these to cover most of your syllabus
              </div>
              <div className="video-grid">
                {tier1Videos.map((video, i) => (
                  <VideoCard key={i} video={video} tier={1} />
                ))}
              </div>
            </div>
          )}

          {/* Tier 2 */}
          {tier2Videos.length > 0 && tier2Videos.some(v => v.video) && (
            <div className="tier-section">
              <div className="tier-header">
                <span className="tier-badge tier2">TIER 2</span>
                Gap Fillers — Dedicated videos for missing topics
              </div>
              <div className="video-grid">
                {tier2Videos
                  .filter(item => item.video)
                  .map((item, i) => (
                    <VideoCard
                      key={i}
                      video={item.video}
                      tier={2}
                      topicName={item.topic_name}
                    />
                  ))
                }
              </div>
            </div>
          )}

          {tier1Videos.length === 0 && tier2Videos.length === 0 && (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
              No video recommendations yet.
            </p>
          )}
        </div>
      )}

      {/* Notes Tab */}
      {activeTab === 'notes' && (
        <NotesViewer notes={notes} topics={topics} />
      )}

      {/* Coverage Tab */}
      {activeTab === 'coverage' && (
        <div className="notes-container">
          {coverageReport.map((item, i) => (
            <div key={i} className="note-accordion">
              <div className="note-header" style={{ cursor: 'default' }}>
                <h3>
                  {item.is_covered ? '✅' : '⚠️'} {item.topic_name}
                </h3>
                <span style={{ color: item.is_covered ? 'var(--success)' : 'var(--warning)' }}>
                  {(item.coverage_score * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ padding: '0 1.5rem 1rem' }}>
                <div className="coverage-bar">
                  <div
                    className="fill"
                    style={{
                      width: `${Math.max(item.coverage_score * 100, 3)}%`,
                      background: item.is_covered
                        ? 'var(--success)'
                        : 'var(--warning)',
                    }}
                  />
                </div>
                {item.best_video_title && (
                  <div style={{
                    marginTop: '0.5rem',
                    fontSize: '0.85rem',
                    color: 'var(--text-muted)',
                  }}>
                    Best match: {item.best_video_title}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Back Link */}
      <div style={{ textAlign: 'center', marginTop: '2rem' }}>
        <Link to="/" className="btn btn-secondary">
          ← Analyze Another Syllabus
        </Link>
      </div>
    </div>
  )
}

export default Results
