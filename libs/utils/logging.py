# libs/utils/logging.py
import logging, re, sys, io

_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]"
)

class EmojiStrippingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        try:
            msg.encode("utf-8")
        except UnicodeEncodeError:
            msg = _EMOJI_RE.sub("", msg)
        return msg

def init_utf8_console_logger(level=logging.INFO, strip_emojis=True):
    # Wrap stdout with UTF-8 if needed
    if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = EmojiStrippingFormatter(fmt) if strip_emojis else logging.Formatter(fmt)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


