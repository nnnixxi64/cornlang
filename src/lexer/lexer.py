import os
from typing import TextIO, Optional

from .token import Token
from .token_type import TokenType
from ..error import CornError

WHITESPACE_CHARS: tuple[str, ...] = (' ', '\t', '\r', '\n')

KEYWORDS: dict[str, TokenType] = {
    'null': TokenType.NULL,
    'mut': TokenType.MUT,
    'return': TokenType.RETURN,
    'native': TokenType.NATIVE,
    'unsafe': TokenType.UNSAFE,
    'safe': TokenType.SAFE,
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'do': TokenType.DO,
    'while': TokenType.WHILE,
    'loop': TokenType.LOOP,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'is': TokenType.IS,
    'as': TokenType.AS,
    'import': TokenType.IMPORT,
    'true': TokenType.TRUE,
    'false': TokenType.FALSE,
}

OPERATORS: dict[str, TokenType] = {
    '?': TokenType.QUESTION,
    '!': TokenType.EXCLAMATION,
    '<<': TokenType.LSHIFT,
    '>>': TokenType.RSHIFT,
    '|': TokenType.OR,
    '&': TokenType.AND,
    '^': TokenType.XOR,
    '>=': TokenType.GE,
    '>': TokenType.GT,
    '<=': TokenType.LE,
    '<': TokenType.LT,
    '!=': TokenType.NE,
    '==': TokenType.EQEQ,
    '=': TokenType.EQ,
    '{': TokenType.LBRACE,
    '}': TokenType.RBRACE,
    '(': TokenType.LPAREN,
    ')': TokenType.RPAREN,
    '+': TokenType.PLUS,
    '-': TokenType.MINUS,
    '*': TokenType.TIMES,
    '/': TokenType.DIVIDE,
    '%': TokenType.MOD,
    '~/': TokenType.TILDE,
    '**': TokenType.POWER,
    ':': TokenType.COLON,
    ',': TokenType.COMMA,
    '.': TokenType.DOT,
    '...': TokenType.VARARGS,
}


class Lexer:
    def __init__(self, file: TextIO):
        self.path: str = os.path.abspath(file.name)
        self.text: str = file.read()
        self.text_length: int = len(self.text)
        self.index: int = 0
        self.line: int = 1
        self.col: int = 1

    def peek(self, offset: int = 0) -> Optional[str]:
        if self.index + offset >= self.text_length:
            return None
        return self.text[self.index + offset]

    def peek_next(self) -> Optional[str]:
        return self.peek(1)

    def advance(self) -> None:
        ch: Optional[str] = self.peek()
        if ch is None:
            return
        self.index += 1
        self.col += 1
        if ch == '\n':
            self.line += 1
            self.col = 1

    def ignore(self) -> None:
        while self.peek() in WHITESPACE_CHARS:
            self.advance()

    def skip_singleline_comment(self) -> None:
        self.advance()
        self.advance()
        while self.peek() is not None and self.peek() != '\n':
            self.advance()

    def skip_multiline_comment(self) -> None:
        self.advance()
        self.advance()
        while True:
            ch: Optional[str] = self.peek()
            if ch is None:
                raise CornError(f"Unterminated multi-line comment at line {self.line} col {self.col}")
            if ch == '*' and self.peek_next() == '/':
                self.advance()
                self.advance()
                break
            self.advance()

    def identifier_token(self, start_line: int, start_col: int) -> Token:
        lexeme: str = ''
        while True:
            ch: Optional[str] = self.peek()
            if ch is None or not (ch.isalnum() or ch == '_'):
                break
            lexeme += ch
            self.advance()
        if lexeme in KEYWORDS:
            return Token(KEYWORDS[lexeme], start_line, start_col)
        return Token(TokenType.IDENTIFIER, start_line, start_col, lexeme)

    def number_token(self, start_line: int, start_col: int) -> Token:
        token_type: TokenType = TokenType.INTEGER
        lexeme: str = ''
        while True:
            ch: Optional[str] = self.peek()
            if ch is None or not (ch.isdigit() or ch in ('.', '_')):
                break
            if ch == '_':
                self.advance()
                continue
            if ch == '.':
                if token_type == TokenType.FLOAT:
                    raise CornError(f"Invalid float format at line {self.line}, col {self.col}")
                token_type = TokenType.FLOAT
            lexeme += ch
            self.advance()
        if lexeme.startswith('.') or lexeme.endswith('.'):
            raise CornError(f"Invalid float format at line {self.line}, col {self.col}")
        return Token(token_type, start_line, start_col, lexeme)

    def string_token(self, start_line: int, start_col: int) -> Token:
        self.advance()
        lexeme: str = ''
        while self.peek() != '"':
            ch: Optional[str] = self.peek()
            if ch is None:
                raise CornError(f"Unterminated string literal at line {self.line}, col {self.col}")
            elif ch == '\\':
                self.advance()
                ch = self.peek()
                if ch is None:
                    raise CornError(f"Unterminated string literal (escape) at line {self.line}, col {self.col}")
                match ch:
                    case 'n':
                        lexeme += '\n'
                    case 't':
                        lexeme += '\t'
                    case 'r':
                        lexeme += '\r'
                    case 'b':
                        lexeme += '\b'
                    case 'f':
                        lexeme += '\u000c'
                    case '\\':
                        lexeme += '\\\\'
                    case '0':
                        lexeme += '\u0000'
                self.advance()
            else:
                lexeme += ch
                self.advance()
        self.advance()
        return Token(TokenType.STRING, start_line, start_col, lexeme)

    def char_token(self, start_line: int, start_col: int) -> Token:
        self.advance()
        lexeme: str = ''
        while self.peek() != '\'':
            ch: Optional[str] = self.peek()
            if ch is None:
                raise CornError(f"Unterminated char literal at line {self.line}, col {self.col}")
            elif ch == '\\':
                lexeme += ch
                self.advance()
                ch = self.peek()
                if ch is None:
                    raise CornError(f"Unterminated char literal (escape) at line {self.line}, col {self.col}")
                lexeme += ch
                self.advance()
            else:
                lexeme += ch
                self.advance()
        self.advance()
        return Token(TokenType.CHARACTER, start_line, start_col, lexeme)

    def op_token(self, start_line: int, start_col: int) -> Token:
        ch: Optional[str] = self.peek()
        next_ch: Optional[str] = self.peek_next()
        if ch is not None and next_ch is not None:
            op: str = ch + next_ch
            if op in OPERATORS:
                self.advance()
                self.advance()
                return Token(OPERATORS[op], start_line, start_col)
        if ch in OPERATORS:
            self.advance()
            return Token(OPERATORS[ch], start_line, start_col)
        raise CornError(f"Unexpected character '{ch}' at line {start_line} col {start_col}")

    def varargs_token(self, start_line: int, start_col: int) -> Token:
        self.advance()
        self.advance()
        self.advance()
        return Token(TokenType.VARARGS, start_line, start_col)

    def next_token(self) -> Token:
        while True:
            ch: Optional[str] = self.peek()
            next_ch: Optional[str] = self.peek_next()
            if ch is None:
                return Token(TokenType.EOF, self.line, self.col)
            if ch in WHITESPACE_CHARS:
                self.ignore()
                continue
            if ch == '/':
                if next_ch is not None and next_ch == '/':
                    self.skip_singleline_comment()
                if next_ch is not None and next_ch == '*':
                    self.skip_multiline_comment()
                continue
            break

        start_line: int = self.line
        start_col: int = self.col
        ch = self.peek()
        next_ch = self.peek_next()
        third_ch: Optional[str] = self.peek(2)
        triple_ch: Optional[str] = None
        if ch is not None and next_ch is not None and third_ch is not None:
            triple_ch = ch + next_ch + third_ch
        if ch is not None and (ch.isalpha() or ch == '_'):
            return self.identifier_token(start_line, start_col)
        if ch is not None and ch.isdigit():
            return self.number_token(start_line, start_col)
        if ch == '"':
            return self.string_token(start_line, start_col)
        if ch == '\'':
            return self.char_token(start_line, start_col)
        if triple_ch is not None and triple_ch == '...':
            return self.varargs_token(start_line, start_col)
        return self.op_token(start_line, start_col)
