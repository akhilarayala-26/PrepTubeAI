import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

function NotesViewer({ notes, topics }) {
  const [openTopic, setOpenTopic] = useState(null)

  const toggleTopic = (topicId) => {
    setOpenTopic(openTopic === topicId ? null : topicId)
  }

  if (!notes || Object.keys(notes).length === 0) {
    return <p style={{ color: 'var(--text-muted)', textAlign: 'center' }}>No notes generated yet.</p>
  }

  return (
    <div className="notes-container">
      {Object.entries(notes).map(([topicId, noteContent]) => {
        const topic = topics?.find(t => t.id === topicId)
        const topicName = topic?.name || topicId
        const isOpen = openTopic === topicId

        return (
          <div key={topicId} className="note-accordion" id={`note-${topicId}`}>
            <div className="note-header" onClick={() => toggleTopic(topicId)}>
              <h3>📝 {topicName}</h3>
              <span className={`arrow ${isOpen ? 'open' : ''}`}>▼</span>
            </div>
            {isOpen && (
              <div className="note-body">
                <ReactMarkdown>{noteContent}</ReactMarkdown>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default NotesViewer
