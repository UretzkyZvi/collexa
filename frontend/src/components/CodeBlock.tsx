"use client";
import { Highlight, themes } from "prism-react-renderer";

export function CodeBlock({ language, code }: { language: string; code: string }) {
  if (language === "text") {
    return <pre className="overflow-auto rounded bg-black/40 p-4 text-xs">{code}</pre>;
  }
  return (
    <Highlight code={code} language={language as any} theme={themes.github}>
      {({ style, tokens, getLineProps, getTokenProps }) => (
        <pre style={style} className="overflow-auto rounded p-4 text-xs">
          {tokens.map((line, i) => (
            <div key={i} {...getLineProps({ line })}>
              {line.map((token, key) => (
                <span key={key} {...getTokenProps({ token })} />
              ))}
            </div>
          ))}
        </pre>
      )}
    </Highlight>
  );
}

