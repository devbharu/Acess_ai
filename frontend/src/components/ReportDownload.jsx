import { memo } from 'react';
import { Download, ExternalLink, FileText } from 'lucide-react';

/**
 * ReportDownload
 * Displays generated formal executive summary PDF reports with direct download and preview actions.
 */
function ReportDownload({ artifact }) {
  if (!artifact) return null;
  const { id, title, file_size, pages, download_url, source_doc } = artifact;
  const sizeKb = file_size ? `${(file_size / 1024).toFixed(1)} KB` : '';

  return (
    <div className="artifact-banner" role="region" aria-label={`Generated document: ${title}`}>
      <div className="artifact-icon-wrap">
        <FileText size={20} />
      </div>
      <div className="artifact-info">
        <strong className="artifact-title">{title}</strong>
        <span className="artifact-meta">
          {pages ? `${pages} page${pages !== 1 ? 's' : ''}` : 'Document'}
          {sizeKb ? ` · ${sizeKb}` : ''}
          {source_doc ? ` · Grounded in: ${source_doc}` : ''}
        </span>
      </div>
      <div className="artifact-actions">
        <a
          href={download_url || `/api/artifacts/${id}/download`}
          download={title}
          className="btn btn-sm btn-primary artifact-btn"
          title={`Download ${title}`}
        >
          <Download size={14} /> Download PDF
        </a>
        {id && (
          <a
            href={`/api/artifacts/${id}/file`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-sm artifact-btn secondary"
            title={`Preview ${title} in a new tab`}
          >
            <ExternalLink size={14} /> View
          </a>
        )}
      </div>
    </div>
  );
}

export default memo(ReportDownload);
