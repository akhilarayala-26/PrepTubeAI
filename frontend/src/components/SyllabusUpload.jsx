import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'

function SyllabusUpload({ onFileSelect, selectedFile }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0])
    }
  }, [onFileSelect])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    multiple: false,
  })

  return (
    <div
      {...getRootProps()}
      className={`upload-zone ${isDragActive ? 'active' : ''} ${selectedFile ? 'active' : ''}`}
      id="syllabus-upload"
    >
      <input {...getInputProps()} />
      <div className="icon">📄</div>
      <h3>
        {isDragActive
          ? 'Drop your syllabus here...'
          : 'Drop your syllabus PDF here'}
      </h3>
      <p>or click to browse files</p>
      {selectedFile && (
        <div className="file-info">
          ✅ {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
        </div>
      )}
    </div>
  )
}

export default SyllabusUpload
