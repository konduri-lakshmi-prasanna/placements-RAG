"""
chart_captioner.py — Multimodal chart-to-text using Claude Vision.

Bar charts in Section 3 are image content. This module sends each
chart image to Claude claude-sonnet-4-20250514 with a structured prompt and gets
back a text description that can be embedded in the vector store.

This is the key RAG challenge: images must become text before indexing.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import anthropic
from loguru import logger

from config import ANTHROPIC_API_KEY, LLM_MODEL


client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CAPTION_PROMPT = """
You are analysing a hiring distribution bar chart for a placement intelligence system.
The chart shows the number of hires across four roles: SDE, Analyst, Officer, and Intern.

Extract ONLY the following information and respond in this exact format:
Company: <company name from chart title>
SDE: <integer>
Analyst: <integer>
Officer: <integer>
Intern: <integer>
Total: <sum>
Summary: <one sentence describing the dominant hiring role>

If you cannot read a bar value precisely, estimate to the nearest 5.
Do not include any other text.
"""


@dataclass
class ChartCaption:
    company:   str
    sde:       int
    analyst:   int
    officer:   int
    intern:    int
    total:     int
    summary:   str
    raw_text:  str         # full LLM response for debugging
    nl_passage: str        # formatted passage for embedding


def _parse_caption(text: str) -> dict:
    """Parse structured LLM response into a dict."""
    result = {}
    for line in text.strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip().lower().replace(" ", "_")] = val.strip()
    return result


def caption_chart(image_bytes: bytes, fallback_company: str = "Unknown") -> ChartCaption:
    """
    Send one chart image to Claude Vision and return a ChartCaption.

    Parameters
    ----------
    image_bytes     : PNG bytes of the chart
    fallback_company: used if the LLM doesn't extract a company name
    """
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type":       "image",
                        "source": {
                            "type":       "base64",
                            "media_type": "image/png",
                            "data":       b64,
                        },
                    },
                    {"type": "text", "text": CAPTION_PROMPT},
                ],
            }],
        )
        raw = response.content[0].text
        parsed = _parse_caption(raw)

        company  = parsed.get("company", fallback_company)
        sde      = int(parsed.get("sde",      0) or 0)
        analyst  = int(parsed.get("analyst",  0) or 0)
        officer  = int(parsed.get("officer",  0) or 0)
        intern   = int(parsed.get("intern",   0) or 0)
        total    = int(parsed.get("total",    sde + analyst + officer + intern) or 0)
        summary  = parsed.get("summary", "")

        nl = (
            f"{company} hiring chart: SDE={sde}, Analyst={analyst}, "
            f"Officer={officer}, Intern={intern}, Total={total}. {summary}"
        )

        logger.info(f"Chart captioned: {company} — {nl}")
        return ChartCaption(
            company=company, sde=sde, analyst=analyst,
            officer=officer, intern=intern, total=total,
            summary=summary, raw_text=raw, nl_passage=nl,
        )

    except Exception as e:
        logger.error(f"Chart captioning failed: {e}")
        # Return empty record so pipeline continues
        return ChartCaption(
            company=fallback_company, sde=0, analyst=0,
            officer=0, intern=0, total=0,
            summary="Chart could not be parsed.",
            raw_text=str(e),
            nl_passage=f"{fallback_company} hiring chart data unavailable.",
        )


def caption_all_charts(images: list[bytes]) -> list[ChartCaption]:
    """Caption a list of chart images in sequence."""
    captions = []
    for i, img in enumerate(images):
        logger.debug(f"Captioning chart {i+1}/{len(images)}")
        caption = caption_chart(img, fallback_company=f"Company_{i+1}")
        captions.append(caption)
    return captions