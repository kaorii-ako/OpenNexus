import { marked } from 'marked'

interface Props { children: string; className?: string }

export default function Markdown({ children, className }: Props) {
  const html = marked.parse(children, { async: false }) as string
  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
