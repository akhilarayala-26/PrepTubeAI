function VideoCard({ video, tier, topicName }) {
  const formatDuration = (seconds) => {
    if (!seconds) return 'Unknown'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    return h > 0 ? `${h}h ${m}m` : `${m}m`
  }

  const formatViews = (count) => {
    if (!count) return ''
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M views`
    if (count >= 1000) return `${(count / 1000).toFixed(0)}K views`
    return `${count} views`
  }

  const videoUrl = video.url || `https://www.youtube.com/watch?v=${video.video_id}`

  return (
    <div className="video-card" id={`video-${video.video_id}`}>
      {video.thumbnail_url && (
        <img
          src={video.thumbnail_url}
          alt={video.title}
          className="thumbnail"
          loading="lazy"
        />
      )}
      <div className="video-info">
        <div className="video-title">{video.title || 'Untitled Video'}</div>
        <div className="video-channel">{video.channel || 'Unknown Channel'}</div>

        <div className="video-meta">
          {video.duration_seconds > 0 && (
            <span className="meta-item">⏱️ {formatDuration(video.duration_seconds)}</span>
          )}
          {video.view_count > 0 && (
            <span className="meta-item">👁️ {formatViews(video.view_count)}</span>
          )}
        </div>

        {tier === 1 && video.covers_topics && (
          <div className="topics-covered">
            {video.covers_topics.map((topic, i) => (
              <span key={i} className="topic-tag">{topic}</span>
            ))}
          </div>
        )}

        {tier === 2 && topicName && (
          <div className="topics-covered">
            <span className="topic-tag uncovered">⚠️ {topicName}</span>
          </div>
        )}

        <a
          href={videoUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="watch-btn"
        >
          ▶ Watch on YouTube
        </a>
      </div>
    </div>
  )
}

export default VideoCard
