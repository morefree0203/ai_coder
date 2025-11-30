from typing import List, Dict, Any
from dataclasses import dataclass, field
import tiktoken
from .prompt import MEMORY_SUMMARIZE_PROMPT
from ..config.settings import settings

@dataclass
class Message:
    role: str
    content: str

@dataclass
class ConversationMemory:
    messages: List[Message] = field(default_factory=list)
    compressed_context: str | None = None
    summarizer_llm = None  # 将由外部注入（LangChain LLM）

    def add(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))

    def as_list(self) -> List[Dict[str, str]]:
        result = []
        if self.compressed_context:
            result.append({"role": "system", "content": f"[COMPRESSED_CONTEXT]\n{self.compressed_context}"})
        for m in self.messages:
            result.append({"role": m.role, "content": m.content})
        return result

    def token_length(self) -> int:
        # 简单估算 token 数 (针对 OpenAI GPT 风格)
        enc = tiktoken.get_encoding("cl100k_base")
        total = 0
        for m in self.messages:
            total += len(enc.encode(m.content))
        if self.compressed_context:
            total += len(enc.encode(self.compressed_context))
        return total

    def maybe_compress(self):
        if len(self.messages) < settings.memory_compress_after:
            return

        # 保留最近 N 条，其余压缩
        keep_last_n = settings.memory_keep_last_n
        old = self.messages[:-keep_last_n]
        if not old:
            return

        history_text = ""
        for idx, msg in enumerate(old, 1):
            history_text += f"{idx}. [{msg.role}] {msg.content}\n"

        prompt = MEMORY_SUMMARIZE_PROMPT.format(history=history_text)
        if self.summarizer_llm is None:
            # 避免异常，直接粗略压缩
            self.compressed_context = "(未使用LLM压缩) 摘要：用户研究目标可能与之前消息相关。"
        else:
            from langchain.prompts import PromptTemplate
            chain = PromptTemplate(template="{text}", input_variables=["text"]).pipe(self.summarizer_llm)
            summary = chain.invoke({"text": prompt})
            if isinstance(summary, str):
                self.compressed_context = summary
            else:
                self.compressed_context = getattr(summary, "content", str(summary))

        # 删除被压缩的历史
        self.messages = self.messages[-keep_last_n:]