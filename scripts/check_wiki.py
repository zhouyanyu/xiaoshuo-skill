#!/usr/bin/env python3
"""Read-only Wiki checks. Standard library only; no external URL or Mermaid syntax checks."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import unquote


@dataclass
class Issue:
    file: Path
    line: int
    message: str
    warning: bool = False


def visible_text(text: str) -> str:
    """Mask code/comments while preserving line numbers for diagnostics."""
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m[0].count("\n"), text, flags=re.S)
    fence = None
    result = []
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line.rstrip())
        if marker:
            run, tail = marker.groups()
            if fence is None:
                fence = (run[0], len(run))
            elif run[0] == fence[0] and len(run) >= fence[1] and not tail.strip():
                fence = None
            result.append("\n" if line.endswith("\n") else "")
        elif fence:
            result.append("\n" if line.endswith("\n") else "")
        else:
            result.append(re.sub(r"(`+).*?\1", "", line))
    return "".join(result)


def has_content(text: str) -> bool:
    text = re.sub(r"\A\ufeff?---\s*\n.*?\n---\s*(?:\n|$)", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    for line in text.splitlines():
        line = line.strip()
        if not line or re.match(r"^#{1,6}\s", line) or re.fullmatch(r"[-|:\s]+", line):
            continue
        if line in {"待补充", "待补充。", "待完善", "TODO", "TBD"}:
            continue
        return True
    return False


def headings(text: str) -> set[str]:
    result, slugs = set(), {}
    for heading in re.findall(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", visible_text(text), re.M):
        heading = re.sub(r"[*_~]", "", heading).strip()
        result.add(heading.casefold())
        slug = re.sub(r"[^\w\-\s]", "", heading.casefold()).replace(" ", "-")
        number = slugs.get(slug, 0)
        slugs[slug] = number + 1
        result.add(slug if number == 0 else f"{slug}-{number}")
    return result


def link_targets(text: str):
    text = visible_text(text)
    for match in re.finditer(r"!?\[\[([^\]\n]+)\]\]", text):
        yield match[1].split("|", 1)[0].strip(), True, text.count("\n", 0, match.start()) + 1
    for match in re.finditer(r"!?\[(?!\[)[^\]\n]*\]\(", text):
        pos, depth = match.end(), 1
        end = pos
        while end < len(text) and depth:
            char = text[end]
            if char == "\\":
                end += 2
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            end += 1
        if depth:
            continue
        raw = text[pos:end - 1].strip()
        if raw.startswith("<") and ">" in raw:
            target = raw[1:raw.index(">")]
        else:
            target = re.split(r'\s+[\'\"]', raw, maxsplit=1)[0].strip()
        yield target, False, text.count("\n", 0, match.start()) + 1
    definitions = {
        m[1].strip().casefold(): m[2] or m[3]
        for m in re.finditer(r"^\s{0,3}\[([^\]^]+)\]:\s*(?:<([^>]+)>|(\S+))", text, re.M)
    }
    for match in re.finditer(r"!?\[([^\]\n]+)\]\[([^\]\n]*)\]", text):
        name = (match[2] or match[1]).strip().casefold()
        line = text.count("\n", 0, match.start()) + 1
        yield definitions.get(name, "@undefined-reference:" + name), False, line


def check(book: Path, vault: Path | None = None, chapters_dir: str = "章节") -> list[Issue]:
    book, vault = book.resolve(), (vault or book).resolve()
    issues = []
    if not book.is_dir():
        return [Issue(book, 0, "书籍档案目录不存在")]
    notes = {p.resolve(): p.read_text(encoding="utf-8-sig") for p in book.rglob("*.md")
             if not any(part in {".git", "归档", "备份"} for part in p.relative_to(book).parts)}
    vault_notes = list(vault.rglob("*.md"))
    homepage = book / "阅读首页.md"
    if not homepage.is_file():
        issues.append(Issue(homepage, 0, "缺少阅读首页.md；不得留下返回不存在首页的链接"))
    elif not has_content(homepage.read_text(encoding="utf-8-sig")):
        issues.append(Issue(homepage, 0, "阅读首页只有标题或占位内容"))
    for source, text in notes.items():
        for target, wiki, line in link_targets(text):
            if target.startswith("@undefined-reference:"):
                issues.append(Issue(source, line, "未定义的 Markdown 引用链接：" + target.split(":", 1)[1]))
                continue
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("//"):
                continue
            rawpath, sep, anchor = target.partition("#")
            rawpath, anchor = unquote(rawpath).replace("\\", "/"), unquote(anchor)
            if not rawpath:
                dest = source
            elif wiki:
                note_path = rawpath if Path(rawpath).suffix else rawpath + ".md"
                candidates = {p.resolve() for p in (vault / note_path, source.parent / note_path) if p.is_file()}
                if not candidates:
                    for p in vault_notes:
                        rel = p.relative_to(vault).as_posix()
                        if rel == note_path or rel.endswith("/" + note_path):
                            candidates.add(p.resolve())
                if len(candidates) > 1:
                    issues.append(Issue(source, line, f"双链目标不唯一，请限定路径：{target}"))
                    continue
                dest = next(iter(candidates), vault / note_path)
            else:
                dest = (vault / rawpath.lstrip("/")) if rawpath.startswith("/") else (source.parent / rawpath)
                dest = dest.resolve()
            if not dest.is_file():
                issues.append(Issue(source, line, f"目标文件不存在：{target}"))
                continue
            if dest.suffix.casefold() != ".md":
                continue
            dest_text = notes.get(dest)
            if dest_text is None:
                dest_text = dest.read_text(encoding="utf-8-sig")
            if not has_content(dest_text):
                issues.append(Issue(source, line, f"目标文件只有标题或占位内容：{target}"))
            if sep and anchor:
                if anchor.startswith("^"):
                    exists = re.search(r"\^" + re.escape(anchor[1:]) + r"\s*$", visible_text(dest_text), re.M)
                else:
                    exists = anchor.casefold() in headings(dest_text)
                if not exists:
                    issues.append(Issue(source, line, f"目标标题／区块不存在：{target}"))
        relative = source.relative_to(book)
        if relative.parts and relative.parts[0] == chapters_dir:
            diagrams = len(re.findall(r"^\s{0,3}(?:`{3,}|~{3,})mermaid\s*$", text, re.M))
            exceptions = set()
            for reason in re.findall(r"^\s*图表例外[：:]\s*(.+)$", visible_text(text), re.M):
                if len(reason) > 12:
                    for kind in ("人物关系图", "场景与行动图"):
                        if kind in reason:
                            exceptions.add(kind)
            if diagrams < 2 - len(exceptions):
                issues.append(Issue(source, 0, f"仅有 {diagrams} 张 Mermaid 图；默认需要场景与行动图、人物关系图"))
        if len(relative.parts) > 1 and relative.parts[0] == "人物":
            if len(re.sub(r"\s", "", visible_text(text))) < 180:
                issues.append(Issue(source, 0, "独立人物页很短：请审查是否应合并到人物索引；不要为通过提示凑字数", True))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", type=Path)
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument("--chapters-dir", default="章节", help="书籍目录下的章节子目录名")
    args = parser.parse_args()
    if args.vault_root and not args.vault_root.is_dir():
        parser.error("--vault-root 必须是已有目录")
    issues = check(args.book, args.vault_root, args.chapters_dir)
    for issue in issues:
        print(f"{'提示' if issue.warning else '错误'} {issue.file}:{issue.line} {issue.message}")
    errors, warnings = sum(not i.warning for i in issues), sum(i.warning for i in issues)
    print(f"检查完成：{errors} 个错误，{warnings} 个提示。未检查剧情事实、外部网页与 Mermaid 渲染。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
