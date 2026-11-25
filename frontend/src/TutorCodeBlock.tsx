import {
  Children,
  isValidElement,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";

function getCodeText(node: ReactNode): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }
  if (Array.isArray(node)) return node.map(getCodeText).join("");
  if (isValidElement(node)) {
    return getCodeText(
      (node.props as { children?: ReactNode }).children
    );
  }
  return "";
}

const keywords = new Set([
  "False", "True", "None", "and", "as", "assert", "async", "await",
  "break", "class", "continue", "def", "del", "elif", "else", "except",
  "finally", "for", "from", "global", "if", "import", "in", "is",
  "lambda", "not", "or", "pass", "raise", "return", "self", "try",
  "while", "with", "yield", "const", "let", "new", "null", "this",
  "throw", "var", "export", "default", "function",
]);

const builtins = new Set([
  "print", "range", "len", "enumerate", "str", "int", "float",
  "list", "dict", "set", "tuple", "sum", "min", "max", "abs",
  "zip", "input", "open",
]);

function highlightCode(code: string, language: string): ReactNode {
  if (!["python", "py", "javascript", "js", "typescript", "ts"].includes(language)) {
    return code;
  }

  const pattern =
    /(#.*|\/\/.*|"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|\b\d+(?:\.\d+)?\b|\b[A-Za-z_$][\w$]*\b|===|!==|==|!=|<=|>=|=>|\+=|-=|\*=|\/=|[=+\-*\/%<>!]|[()[\]{}.,:;])/gm;

  const result: ReactNode[] = [];
  let cursor = 0;
  let index = 0;

  for (const match of code.matchAll(pattern)) {
    const token = match[0];
    const start = match.index ?? 0;

    if (start > cursor) result.push(code.slice(cursor, start));

    let kind = "punctuation";

    if (token.startsWith("#") || token.startsWith("//")) {
      kind = "comment";
    } else if (/^["'`]/.test(token)) {
      kind = "string";
    } else if (/^\d/.test(token)) {
      kind = "number";
    } else if (keywords.has(token)) {
      kind = "keyword";
    } else if (builtins.has(token)) {
      kind = "builtin";
    } else if (/^[A-Za-z_$][\w$]*$/.test(token)) {
      kind = /^\s*\(/.test(code.slice(start + token.length))
        ? "function"
        : "identifier";
    } else if (/^(===|!==|==|!=|<=|>=|=>|\+=|-=|\*=|\/=|[=+\-*\/%<>!])$/.test(token)) {
      kind = "operator";
    }

    result.push(
      <span className={`cg-code-token ${kind}`} key={`token-${index++}`}>
        {token}
      </span>
    );

    cursor = start + token.length;
  }

  if (cursor < code.length) result.push(code.slice(cursor));
  return result;
}

export default function TutorCodeBlock({
  children,
}: {
  children: ReactNode;
}) {
  const [copyLabel, setCopyLabel] = useState("Copy code");

  const codeElement = Children.toArray(children).find(isValidElement) as
    | ReactElement<{ className?: string; children?: ReactNode }>
    | undefined;

  const className = codeElement?.props.className || "";
  const language = className.match(/language-([\w+-]+)/)?.[1]?.toLowerCase() || "";
  const code = getCodeText(codeElement?.props.children ?? children).replace(/\n$/, "");

  async function copyCode() {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(code);
      } else {
        const area = document.createElement("textarea");
        area.value = code;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.left = "-9999px";
        document.body.appendChild(area);
        area.select();

        const copied = document.execCommand("copy");
        area.remove();
        if (!copied) throw new Error("Copy failed");
      }

      setCopyLabel("Copied!");
    } catch {
      setCopyLabel("Copy failed");
    }

    window.setTimeout(() => setCopyLabel("Copy code"), 1800);
  }

  return (
    <div className="cg-code-card">
      <div className="cg-code-toolbar">
        <span className="cg-code-language">{language || "CODE"}</span>
        <button
          type="button"
          className="cg-code-copy"
          onClick={() => void copyCode()}
          aria-label="Copy code to clipboard"
        >
          {copyLabel}
        </button>
      </div>
      <pre className="cg-code-pre">
        <code className={language ? `language-${language}` : undefined}>
          {highlightCode(code, language)}
        </code>
      </pre>
    </div>
  );
}
