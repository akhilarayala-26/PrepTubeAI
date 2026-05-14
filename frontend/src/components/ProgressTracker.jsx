function ProgressTracker({ messages, currentStep, status }) {
  const steps = [
    { key: 'parse_syllabus', label: 'Parsing syllabus...', icon: '📄' },
    { key: 'search_youtube', label: 'Searching YouTube...', icon: '🔍' },
    { key: 'fetch_transcripts', label: 'Fetching transcripts...', icon: '📝' },
    { key: 'score_coverage', label: 'Scoring coverage...', icon: '📊' },
    { key: 'rewrite_queries', label: 'Rewriting queries (retry)...', icon: '🔄' },
    { key: 'fallback_search', label: 'Finding gap fillers...', icon: '📌' },
    { key: 'generate_notes', label: 'Generating study notes...', icon: '✍️' },
  ]

  const getStepStatus = (stepKey) => {
    const stepIndex = steps.findIndex(s => s.key === stepKey)
    const currentIndex = steps.findIndex(s => s.key === currentStep)

    if (status === 'completed') return 'done'
    if (stepIndex < currentIndex) return 'done'
    if (stepIndex === currentIndex) return 'active'
    return 'pending'
  }

  const getIcon = (stepKey) => {
    const s = getStepStatus(stepKey)
    if (s === 'done') return '✅'
    if (s === 'active') return '🔄'
    return '⏳'
  }

  // Filter out steps that weren't used (e.g., rewrite/fallback if not needed)
  const activeSteps = steps.filter(step => {
    if (step.key === 'rewrite_queries' || step.key === 'fallback_search') {
      return messages.some(m => m.includes('Retry') || m.includes('Fallback'))
    }
    return true
  })

  return (
    <div className="progress-section">
      <div className="progress-title">📊 Progress</div>
      <div className="progress-steps">
        {activeSteps.map((step) => (
          <div
            key={step.key}
            className={`progress-step ${getStepStatus(step.key)}`}
          >
            <span className="step-icon">{getIcon(step.key)}</span>
            <span className="step-text">
              {messages.find(m => m.includes(step.label.split('...')[0])) || step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ProgressTracker
