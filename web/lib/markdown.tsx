import type { ReactNode } from "react";

type Block =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; lines: string[] }
  | { type: "blockquote"; lines: string[] }
  | { type: "list"; items: string[] }
  | { type: "table"; rows: string[][] }
  | { type: "code"; code: string };

const headingClass: Record<number, string> = {
  1: "text-2xl md:text-3xl font-bold text-gray-950 mt-0 mb-4 scroll-mt-24",
  2: "text-xl md:text-2xl font-bold text-[#1F4E79] mt-10 mb-4 pb-2 border-b border-blue-100 scroll-mt-24",
  3: "text-lg font-bold text-gray-900 mt-8 mb-3 scroll-mt-24",
  4: "text-base font-bold text-gray-800 mt-6 mb-2 scroll-mt-24",
  5: "text-sm font-bold text-gray-700 mt-5 mb-2 scroll-mt-24",
  6: "text-sm font-bold text-gray-700 mt-5 mb-2 scroll-mt-24",
};

function slugify(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^\p{L}\p{N}-]/gu, "")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

export function parseMarkdown(markdown: string): Block[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === "" || line.trim() === "---") {
      i += 1;
      continue;
    }

    if (line.startsWith("```")) {
      const codeLines: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i += 1;
      }
      blocks.push({ type: "code", code: codeLines.join("\n") });
      i += 1;
      continue;
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      blocks.push({
        type: "heading",
        level: heading[1].length,
        text: heading[2],
      });
      i += 1;
      continue;
    }

    if (line.startsWith(">")) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].startsWith(">")) {
        quoteLines.push(lines[i].replace(/^>\s?/, ""));
        i += 1;
      }
      blocks.push({ type: "blockquote", lines: quoteLines });
      continue;
    }

    if (isTableStart(lines, i)) {
      const rows: string[][] = [];
      rows.push(splitTableRow(lines[i]));
      i += 2;
      while (i < lines.length && isTableRow(lines[i])) {
        rows.push(splitTableRow(lines[i]));
        i += 1;
      }
      blocks.push({ type: "table", rows });
      continue;
    }

    if (/^- .+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^- .+/.test(lines[i])) {
        items.push(lines[i].replace(/^- /, ""));
        i += 1;
      }
      blocks.push({ type: "list", items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      lines[i].trim() !== "---" &&
      !lines[i].startsWith("```") &&
      !/^(#{1,6})\s+/.test(lines[i]) &&
      !lines[i].startsWith(">") &&
      !isTableStart(lines, i) &&
      !/^- .+/.test(lines[i])
    ) {
      paragraphLines.push(lines[i]);
      i += 1;
    }
    blocks.push({ type: "paragraph", lines: paragraphLines });
  }

  return blocks;
}

export function renderMarkdown(markdown: string): ReactNode {
  return parseMarkdown(markdown).map((block, index) => {
    if (block.type === "heading") {
      return renderHeading(block.level, block.text, index);
    }

    if (block.type === "paragraph") {
      return (
        <p key={index} className="my-4 text-sm leading-7 text-gray-700">
          {renderInline(block.lines.join(" "))}
        </p>
      );
    }

    if (block.type === "blockquote") {
      return (
        <blockquote
          key={index}
          className="my-5 border-l-4 border-[#2E73AC] bg-blue-50/70 px-4 py-3 text-sm leading-7 text-gray-700"
        >
          {block.lines.map((line, lineIndex) => (
            <p key={lineIndex}>{renderInline(line)}</p>
          ))}
        </blockquote>
      );
    }

    if (block.type === "list") {
      return (
        <ul
          key={index}
          className="my-4 list-disc space-y-1 pl-6 text-sm leading-7 text-gray-700"
        >
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item)}</li>
          ))}
        </ul>
      );
    }

    if (block.type === "table") {
      const [head, ...body] = block.rows;
      return (
        <div key={index} className="my-6 overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full border-collapse bg-white text-sm">
            <thead className="bg-[#1F4E79] text-white">
              <tr>
                {head.map((cell, cellIndex) => (
                  <th
                    key={cellIndex}
                    className="border-r border-white/20 px-3 py-2 text-left font-bold last:border-r-0"
                  >
                    {renderInline(cell)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row, rowIndex) => (
                <tr key={rowIndex} className="odd:bg-white even:bg-slate-50">
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      className="border-r border-t border-gray-200 px-3 py-2 align-top text-gray-700 last:border-r-0"
                    >
                      {renderInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    return (
      <pre
        key={index}
        className="my-5 overflow-x-auto rounded-lg bg-gray-950 p-4 text-xs leading-6 text-emerald-300"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {block.code}
      </pre>
    );
  });
}

function renderHeading(level: number, text: string, key: number): ReactNode {
  const className = headingClass[level];
  const id = slugify(text);
  if (level === 1) {
    return (
      <h1 key={key} id={id} className={className}>
        {renderInline(text)}
      </h1>
    );
  }
  if (level === 2) {
    return (
      <h2 key={key} id={id} className={className}>
        {renderInline(text)}
      </h2>
    );
  }
  if (level === 3) {
    return (
      <h3 key={key} id={id} className={className}>
        {renderInline(text)}
      </h3>
    );
  }
  if (level === 4) {
    return (
      <h4 key={key} id={id} className={className}>
        {renderInline(text)}
      </h4>
    );
  }
  if (level === 5) {
    return (
      <h5 key={key} id={id} className={className}>
        {renderInline(text)}
      </h5>
    );
  }
  return (
    <h6 key={key} id={id} className={className}>
      {renderInline(text)}
    </h6>
  );
}

function isTableStart(lines: string[], index: number): boolean {
  return isTableRow(lines[index]) && index + 1 < lines.length && isDividerRow(lines[index + 1]);
}

function isTableRow(line: string): boolean {
  return /^\|.+\|$/.test(line.trim());
}

function isDividerRow(line: string): boolean {
  return /^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(line.trim());
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function renderInline(text: string): ReactNode[] {
  const parts = text
    .split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g)
    .filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={index}
          className="rounded bg-gray-100 px-1.5 py-0.5 text-[0.85em] text-gray-900"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-bold text-gray-950">
          {part.slice(2, -2)}
        </strong>
      );
    }
    const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(part);
    if (link) {
      const [, label, href] = link;
      const isAnchor = href.startsWith("#");
      const isExternal = /^https?:\/\//.test(href);
      return (
        <a
          key={index}
          href={href}
          className="text-[#2E73AC] underline-offset-2 hover:underline hover:text-[#1F4E79]"
          {...(isExternal && !isAnchor
            ? { target: "_blank", rel: "noreferrer" }
            : {})}
        >
          {label}
        </a>
      );
    }
    return <span key={index}>{part}</span>;
  });
}
