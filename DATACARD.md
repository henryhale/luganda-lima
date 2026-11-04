---
pretty_name: luganda-lima
license: cc-by-4.0
language:
- lg
task_categories:
- text-generation
size_categories:
- n<1K
configs:
- config_name: default
  data_files: processed/all.jsonl
---

# luganda-lima

[![GitHub](https://img.shields.io/badge/GitHub-henryhale%2Fluganda--lima-181717?logo=github)](https://github.com/henryhale/luganda-lima)
![Language](https://img.shields.io/badge/language-Luganda-blue)
![Conversations](https://img.shields.io/badge/conversations-685-green)
[![LIMA paper](https://img.shields.io/badge/arXiv-2305.11206-b31b1b?logo=arxiv)](https://arxiv.org/abs/2305.11206)
[![License](https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey)](https://creativecommons.org/licenses/by/4.0/)

A small set of synthetic, multi-turn Luganda user–assistant conversations for
LIMA-style (*Less Is More for Alignment*) fine-tuning.

| Source model | `source` value | Conversations | Messages |
|---|---|---:|---:|
| ChatGPT 5.5 | `chatgpt-5.5` | 175 | 1,515 |
| Gemini 3.8 Flash (medium) | `gemini-3.8-flash-medium` | 410 | 1,722 |
| Qwen3.7-Plus | `qwen3.7-plus` | 100 | 800 |
| **Total** | | **685** | **4,037** |

## Format

`processed/all.jsonl`, one conversation per line:

```json
{"id": "chatgpt-5.5-0001", "source": "chatgpt-5.5", "source_file": "chatgpt-5.5/1.txt", "messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

Model self-identification is replaced with a generic assistant. Raw generations
are in `data/`; rebuild with `python preprocess.py`.

## Acknowledgements

Conversations were generated with ChatGPT 5.5 (OpenAI), Gemini 3.8 Flash (Google)
and Qwen3.7-Plus (Alibaba Qwen team). The name follows [LIMA: Less Is More for
Alignment](https://arxiv.org/abs/2305.11206) (Zhou et al., 2023).

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The text is model-generated;
use must also comply with the terms of the models listed above.
