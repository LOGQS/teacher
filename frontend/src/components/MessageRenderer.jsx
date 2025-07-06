import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

const MessageRenderer = ({ content, className = '' }) => {
  // Handle empty or null content
  if (!content || typeof content !== 'string') {
    return <div className={className}>No content</div>
  }

  return (
    <div className={`message-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Style code blocks
          code: ({ node, inline, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '')
            return !inline ? (
              <pre className="bg-dark-bg/30 border border-dark-border/50 rounded-lg p-3 overflow-x-auto my-2 text-xs">
                <code className={`${className} text-dark-text`} {...props}>
                  {children}
                </code>
              </pre>
            ) : (
              <code className="bg-dark-bg/30 border border-dark-border/50 px-1.5 py-0.5 rounded text-xs font-mono text-dark-text" {...props}>
                {children}
              </code>
            )
          },
          // Style headings
          h1: ({ children }) => (
            <h1 className="text-base font-bold mt-3 mb-2 text-dark-text first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-bold mt-2 mb-1 text-dark-text first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold mt-2 mb-1 text-dark-text first:mt-0">
              {children}
            </h3>
          ),
          // Style lists
          ul: ({ children }) => (
            <ul className="list-disc list-inside my-1 space-y-0.5 pl-3 text-sm">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside my-1 space-y-0.5 pl-3 text-sm">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-dark-text-secondary leading-relaxed">
              {children}
            </li>
          ),
          // Style paragraphs
          p: ({ children }) => (
            <p className="mb-1 leading-relaxed last:mb-0 text-sm">
              {children}
            </p>
          ),
          // Style blockquotes
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-ios-blue pl-4 my-2 italic text-dark-text-secondary">
              {children}
            </blockquote>
          ),
          // Style tables
          table: ({ children }) => (
            <div className="overflow-x-auto my-2">
              <table className="min-w-full border border-dark-border rounded-lg">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-dark-border">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-dark-border">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-dark-border/50">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-left text-sm font-semibold text-dark-text">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-sm text-dark-text-secondary">
              {children}
            </td>
          ),
          // Style links
          a: ({ children, href }) => (
            <a 
              href={href} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-ios-blue hover:text-blue-400 underline"
            >
              {children}
            </a>
          ),
          // Style horizontal rules
          hr: () => (
            <hr className="my-4 border-dark-border" />
          ),
          // Style strong/bold text
          strong: ({ children }) => (
            <strong className="font-semibold text-dark-text">
              {children}
            </strong>
          ),
          // Style emphasis/italic text
          em: ({ children }) => (
            <em className="italic text-dark-text">
              {children}
            </em>
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default MessageRenderer