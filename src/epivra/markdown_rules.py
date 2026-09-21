"""Shared author math grammar; raw expressions are retained for export."""


def math_plugin(parser):
    def inline(state, silent):
        start = state.pos
        rest = state.src[start:]
        opener = next((x for x in (r"\(", r"\[", "$$", "$") if rest.startswith(x)), None)
        if not opener or (opener == "$" and (len(rest) < 2 or rest[1].isspace())):
            return False
        closer = {r"\(": r"\)", r"\[": r"\]"}.get(opener, opener)
        end = state.src.find(closer, start + len(opener))
        if end < 0 or "\n" in state.src[start:end]:
            return False
        if opener == "$" and (state.src[end - 1].isspace() or state.src[end + 1:end + 2].isdigit()):
            return False
        if not silent:
            token = state.push("math_inline", "math", 0)
            token.content = state.src[start:end + len(closer)]
        state.pos = end + len(closer)
        return True

    def block(state, start, end, silent):
        first = state.bMarks[start] + state.tShift[start]
        line = state.src[first:state.eMarks[start]]
        opener = "$$" if line.startswith("$$") else r"\[" if line.startswith(r"\[") else None
        if not opener:
            return False
        closer = "$$" if opener == "$$" else r"\]"
        last, text = start, line[2:]
        while True:
            closing = text.find(closer)
            if closing >= 0:
                if text[closing + len(closer):].strip():
                    return False
                break
            last += 1
            if last >= end:
                return False
            text += "\n" + state.getLines(last, last + 1, state.blkIndent, False)
        if silent:
            return True
        token = state.push("math_block", "math", 0)
        token.block = True
        token.content = opener + text
        token.map = [start, last + 1]
        state.line = last + 1
        return True

    parser.inline.ruler.before("escape", "math_inline", inline)
    parser.block.ruler.before("fence", "math_block", block)
    return parser
