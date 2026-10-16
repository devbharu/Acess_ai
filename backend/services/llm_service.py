import json
import logging
import re
import requests
from typing import Generator, List, Dict, Any, Optional
from ..config import OLLAMA_BASE_URL, DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class LLMService:
    @staticmethod
    def stream_chat(
        messages: List[Dict[str, str]],
        evidence: List[Dict[str, Any]],
        settings: Dict[str, Any],
        images: Optional[List[str]] = None
    ) -> Generator[str, None, None]:
        """
        Stream response tokens from Ollama with grounded evidence context.
        For multimodal models like Gemma, passes base64 images directly.
        Falls back to rule-based grounded extraction if Ollama is unreachable.
        """
        import os
        from .agent_service import normalize_model_name
        from .vision_service import VisionService

        model = normalize_model_name(settings.get("model", "gemma4:31b-cloud"))
        system_prompt = settings.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        temperature = float(settings.get("temperature", 0.3))
        top_p = float(settings.get("top_p", 0.9))
        top_k = int(settings.get("top_k", 40))
        num_ctx = int(settings.get("num_ctx", 8192))
        num_predict = int(settings.get("num_predict", 1024))
        repeat_penalty = float(settings.get("repeat_penalty", 1.1))
        seed = settings.get("seed")

        is_vision = VisionService.is_vision_model(model)

        # Collect base64 images for multimodal models (e.g. Gemma 4 31B)
        b64_images: List[str] = []
        if is_vision:
            if images:
                for img_item in images:
                    if not img_item:
                        continue
                    if os.path.exists(img_item):
                        b64 = VisionService.encode_image_base64(img_item)
                        if b64 and b64 not in b64_images:
                            b64_images.append(b64)
                    elif len(img_item) > 100:
                        if img_item not in b64_images:
                            b64_images.append(img_item)

            for e in evidence:
                if e.get("type") in ("image", "ocr") or e.get("kind") == "image":
                    if e.get("image_b64") and e["image_b64"] not in b64_images:
                        b64_images.append(e["image_b64"])
                    elif e.get("file_path") and os.path.exists(e["file_path"]):
                        b64 = VisionService.encode_image_base64(e["file_path"])
                        if b64 and b64 not in b64_images:
                            b64_images.append(b64)

            b64_images = b64_images[:3]

        # Format evidence section
        evidence_lines = []
        for e in evidence:
            src = e.get("source") or e.get("filename", "file")
            page = e.get("page")
            etype = e.get("type", "evidence")
            header = f"[{etype.upper()}: {src}" + (f", page {page}" if page else "") + "]"
            txt = e.get("text") or e.get("evidence") or e.get("image_description") or ""
            evidence_lines.append(f"{header}\n{txt}")

        evidence_block = "\n\n".join(evidence_lines) if evidence_lines else "No specific documents or images attached."

        full_system = f"{system_prompt}\n\n=== VERIFIED EVIDENCE ===\n{evidence_block}\n=== END EVIDENCE ==="

        # Build payload for Ollama
        ollama_messages = [{"role": "system", "content": full_system}]
        for m in messages:
            ollama_messages.append({"role": m["role"], "content": m["content"]})

        # Attach images directly to the user message for multimodal models (Gemma)
        if is_vision and b64_images:
            for m in reversed(ollama_messages):
                if m.get("role") == "user":
                    m["images"] = b64_images
                    break

        options = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "repeat_penalty": repeat_penalty,
        }
        if seed is not None:
            options["seed"] = int(seed)

        payload = {
            "model": model,
            "messages": ollama_messages,
            "options": options,
            "stream": True,
        }

        # Try streaming from Ollama
        try:
            res = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                stream=True,
                timeout=(5, 60),
            )
            if res.status_code == 200:
                for line in res.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode("utf-8"))
                        msg = data.get("message", {})
                        content = msg.get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
                            return
                    except Exception:
                        continue
                return
            else:
                logger.warning("Ollama /api/chat returned status %d", res.status_code)
        except Exception as e:
            logger.warning("Ollama call failed (%s), using grounded fallback responder", e)

        # Grounded reasoning fallback
        latest_question = messages[-1]["content"] if messages else ""
        yield from LLMService._grounded_fallback(latest_question, evidence)

    @staticmethod
    def _grounded_fallback(question: str, evidence: List[Dict[str, Any]]) -> Generator[str, None, None]:
        if not evidence:
            yield "I examined your files and conversation context, but could not find information addressing that specific question. Please attach the relevant document or image."
            return

        combined_text = "\n\n".join([e.get("text", "") for e in evidence if e.get("text")])
        q_lower = question.lower()
        src_names = list({e.get("source") or e.get("filename") for e in evidence if e.get("source") or e.get("filename")})
        doc_ref = f" from `{src_names[0]}`" if src_names else ""

        # 0. Images and Visual Analysis
        img_evidence = [e for e in evidence if e.get("type") == "image" or e.get("kind") == "image" or e.get("image_description")]
        if img_evidence and (any(w in q_lower for w in ["image", "picture", "photo", "logo", "graphic", "aimge", "what this", "describe", "look like", "see", "visual", "show"]) or not any(w in q_lower for w in ["amount", "date", "payment", "due"])):
            target_ev = img_evidence[0]
            desc = target_ev.get("image_description") or target_ev.get("text") or ""
            src_name = target_ev.get("source") or target_ev.get("filename") or "image"
            yield f"### Visual Description of `{src_name}`\n\n{desc}"
            return

        # 1. Amounts
        if any(w in q_lower for w in ["amount", "payment", "cost", "total", "price", "fee", "how much"]):
            amounts = re.findall(r"[\$€£₹]?\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?", combined_text)
            money_matches = [a.strip() for a in amounts if any(c.isdigit() for c in a) and len(a.strip()) > 1]
            if money_matches:
                yield f"Based on the provided evidence{doc_ref}, the amount found is **{money_matches[0]}**."
                return

        # 2. Dates
        if any(w in q_lower for w in ["date", "due", "when", "deadline"]):
            dates = re.findall(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4}|\d{1,2} \w+ \d{4})\b", combined_text)
            if dates:
                yield f"According to the evidence{doc_ref}, the relevant date indicated is **{dates[0]}**."
                return

        # 3. Summary / Key Points / Overview
        if any(w in q_lower for w in ["summarize", "summary", "key points", "overview", "what is in", "what is there", "what does this pdf", "main points"]):
            yield f"### Summary & Key Points{doc_ref}\n\n"
            paragraphs = [p.strip() for p in combined_text.split("\n\n") if len(p.strip()) > 40]
            if paragraphs:
                yield f"**Overview**:\n{paragraphs[0]}\n\n"
                if len(paragraphs) > 1:
                    yield "**Key Highlights**:\n"
                    for idx, p in enumerate(paragraphs[1:5], 1):
                        first_sentence = p.split(".")[0].strip()
                        if first_sentence:
                            yield f"- {first_sentence}.\n"
            else:
                yield f"{combined_text[:600]}...\n"
            return

        # 4. Topics / Outline / What else is there
        if any(w in q_lower for w in ["topics", "topic", "outline", "what else", "table of contents", "sections", "chapters"]):
            yield f"### Topics & Content Covered{doc_ref}\n\n"
            headings = [line.strip().lstrip("#").strip() for line in combined_text.split("\n") if line.strip().startswith(("#", "Section", "Topic", "Chapter", "1.", "2.", "3.", "4."))]
            if headings:
                for idx, h in enumerate(headings[:8], 1):
                    yield f"{idx}. **{h}**\n"
            else:
                paragraphs = [p.strip() for p in combined_text.split("\n\n") if len(p.strip()) > 30]
                for idx, p in enumerate(paragraphs[:5], 1):
                    yield f"{idx}. {p[:120]}...\n"
            return

        # 5. Detail / More info / Explain
        paragraphs = [p.strip() for p in combined_text.split("\n\n") if p.strip()]
        if paragraphs:
            lead = paragraphs[0]
            rest = "\n\n".join(paragraphs[1:4])
            yield f"### Detailed Analysis{doc_ref}\n\n{lead}\n\n{rest}"
        else:
            yield f"Based on {src_names[0] if src_names else 'the document'}: {combined_text[:500]}"

    @staticmethod
    def generate_follow_ups(
        user_message: str,
        answer: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Dynamically generate 3 contextual, intelligent follow-up question suggestions
        using the LLM based on user message, answer, and evidence.
        Falls back to intelligent extraction of concepts/headings from the answer if Ollama is unreachable.
        """
        settings = settings or {}
        model = settings.get("model", "gemma4:31b-cloud")
        user_msg = (user_message or "").strip()
        ans_snip = (answer or "").strip()[:800]
        evidence = evidence or []

        # Build concise evidence summary
        evidence_snippets = []
        for e in evidence[:4]:
            src = e.get("source") or e.get("filename") or "document"
            text = (e.get("text") or "").strip()[:200]
            if text:
                evidence_snippets.append(f"[{src}]: {text}")
        ev_block = "\n".join(evidence_snippets) if evidence_snippets else "None"

        prompt = (
            f"You are AccessAI. Based on this conversation and context, "
            f"suggest exactly 3 concise, highly relevant follow-up questions the user might want to ask next.\n\n"
            f"Context / Evidence:\n{ev_block}\n\n"
            f"User Question: {user_msg}\n"
            f"AI Answer: {ans_snip}\n\n"
            f"Rules:\n"
            f"- Questions must be specific to the concepts, components, code, or details mentioned above.\n"
            f"- Do NOT suggest generic questions like 'Can you explain this in more detail?' or 'Summarize the key points'.\n"
            f"- Keep each question short, natural, and under 12 words.\n"
            f"- Return ONLY a JSON list of 3 strings: [\"Question 1?\", \"Question 2?\", \"Question 3?\"]."
        )

        try:
            res = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {
                        "temperature": 0.4,
                        "num_predict": 120,
                    },
                },
                timeout=3.5,
            )
            if res.status_code == 200:
                raw = res.json().get("response", "").strip()
                if raw.startswith("```"):
                    raw = re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                data = json.loads(raw.strip())
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    for k in ["questions", "follow_ups", "follow_up_questions", "suggestions"]:
                        if k in data and isinstance(data[k], list):
                            items = data[k]
                            break

                valid_questions = []
                for q in items:
                    if isinstance(q, str):
                        q_clean = q.strip().strip('"').strip("'")
                        if len(q_clean) >= 6:
                            if not q_clean.endswith("?"):
                                q_clean += "?"
                            if q_clean not in valid_questions:
                                valid_questions.append(q_clean)
                if len(valid_questions) >= 2:
                    return valid_questions[:3]
        except Exception as e:
            logger.info("Ollama generate_follow_ups skipped or timed out (%s), using dynamic concept extraction", e)

        return LLMService._dynamic_follow_up_fallback(user_msg, answer, evidence)

    @staticmethod
    def _dynamic_follow_up_fallback(user_msg: str, answer: str, evidence: List[Dict[str, Any]]) -> List[str]:
        """
        Dynamically synthesize relevant follow-up questions from actual headings,
        code tokens, named concepts, and source documents when LLM generation is unavailable.
        """
        questions = []
        combined = f"{user_msg}\n{answer}\n" + "\n".join([e.get("text", "") for e in (evidence or [])])
        src_names = [e.get("source") or e.get("filename") for e in (evidence or []) if e.get("source") or e.get("filename")]
        primary_src = src_names[0] if src_names else None

        # 1. Backticked code tokens or technical identifiers (e.g. `pinMode`, `digitalRead`, `debouncing`)
        code_terms = re.findall(r"`([^`]+)`", answer)
        for term in code_terms:
            clean = term.strip()
            if len(clean) > 2 and clean.lower() not in ["true", "false", "none", "null", "undefined"]:
                q = f"How is `{clean}` configured in this implementation?"
                if q not in questions:
                    questions.append(q)
                if len(questions) >= 3:
                    return questions

        # 2. Markdown headings or section titles in the answer (e.g. "### Code Implementation")
        headings = re.findall(r"(?:^|\n)#{1,3}\s+([^\n]+)", answer)
        for h in headings:
            h_clean = h.strip()
            if len(h_clean) > 3 and not any(w in h_clean.lower() for w in ["summary", "overview", "analysis", "result"]):
                q = f"Can you walk through the {h_clean} step by step?"
                if q not in questions:
                    questions.append(q)
                if len(questions) >= 3:
                    return questions

        # 3. Specific domain concepts detected in the content
        concept_patterns = [
            (r"\bdebounc(?:ing|e)?\b", "How does the debouncing logic prevent false triggers in this circuit?"),
            (r"\bresistor\b", "What resistor values and pin connections are specified?"),
            (r"\b(?:led|diode)\b", "How does the digital output control the LED state?"),
            (r"\bpush\s*button\b", "How is the push button input processed in this setup?"),
            (r"\b(?:arduino|microcontroller)\b", "Can you show the complete pin configuration for this sketch?"),
            (r"\b(?:welding|robot)\b", "What safety protocols and operating parameters are required for this welding robot?"),
            (r"\b(?:solar|photovoltaic)\b", "What are the efficiency metrics and specifications of this solar system?"),
            (r"\b(?:cnc|3d print)\b", "What materials and machine tolerances are used in this process?"),
            (r"\b(?:amount|cost|price|fee)\b", "Are there any additional breakdown fees or line items mentioned?"),
            (r"\b(?:deadline|due date|schedule)\b", "What subsequent milestones follow this date?"),
        ]
        for pat, q in concept_patterns:
            if re.search(pat, combined, re.IGNORECASE) and q not in questions:
                questions.append(q)
                if len(questions) >= 3:
                    return questions

        # 4. Prominent multi-word capitalized entities (e.g. "Dr V M Aparanji", "Department of E&CE")
        cap_phrases = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b", answer)
        for phrase in cap_phrases:
            phrase_clean = phrase.strip()
            if phrase_clean.lower() not in ["access ai", "the arduino", "overview analysis", "based on", "can you", "key highlights"]:
                q = f"What role does {phrase_clean} play in this context?"
                if q not in questions:
                    questions.append(q)
                if len(questions) >= 3:
                    return questions

        # 5. Document-specific inquiry if source is available
        if primary_src and len(questions) < 3:
            questions.append(f"What additional topics or sections are covered in {primary_src}?")

        if not questions:
            sentences = [s.strip() for s in re.split(r"[.\n]", answer) if len(s.strip()) > 20]
            if sentences:
                questions.append(f"Can you provide more details about '{sentences[0][:60]}...'?")

        return questions[:3]

    @staticmethod
    def generate_chat_title(
        user_message: str,
        answer: str = "",
        sources: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Dynamically generate a concise 2-3 word chat title using the AI model
        based on the user's inquiry, context, and assistant answer.
        Falls back to intelligent entity extraction if Ollama is unreachable.
        """
        settings = settings or {}
        model = settings.get("model", "gemma4:31b-cloud")
        user_msg = (user_message or "").strip()
        ans_snip = (answer or "").strip()[:400]
        sources = sources or []

        src_names = [s.get("source") or s.get("filename") for s in sources if s.get("source") or s.get("filename")]
        src_context = f"Referenced File: {src_names[0]}" if src_names else ""
        ans_context = f"Answer Summary: {ans_snip}" if ans_snip else ""

        context_lines = [line for line in [src_context, ans_context] if line]
        extra_ctx = ("\n" + "\n".join(context_lines)) if context_lines else ""

        prompt = (
            f"You are AccessAI. Generate a concise, natural 2-to-3 word title for this conversation "
            f"based on the first message sent to the AI by the user.\n\n"
            f"First User Message: {user_msg}{extra_ctx}\n\n"
            f"Rules:\n"
            f"- Output strictly 2 or 3 words (at most 4 words).\n"
            f"- Title Case (e.g. 'Arduino Push Button' or 'Solar Energy Overview').\n"
            f"- Do NOT use quotes, trailing punctuation, or generic filler like 'Chat', 'Conversation', 'Session'.\n"
            f"- Return ONLY the 2-3 word title text."
        )

        try:
            res = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 15,
                    },
                },
                timeout=2.5,
            )
            if res.status_code == 200:
                raw = res.json().get("response", "").strip()
                cleaned = re.sub(r'[\'"`.]', '', raw).strip()
                words = cleaned.split()
                if 1 <= len(words) <= 4:
                    return " ".join([w.capitalize() for w in words[:3]])
        except Exception as e:
            logger.info("generate_chat_title skipped/timed out (%s), using dynamic fallback", e)

        return LLMService._dynamic_title_fallback(user_msg, answer, sources)

    @staticmethod
    def _dynamic_title_fallback(user_msg: str, answer: str, sources: List[Dict[str, Any]]) -> str:
        """
        Dynamically extract a concise 2-3 word title from domain keywords, headings, or source files.
        """
        combined = f"{user_msg} {answer}"

        if re.search(r"\barduino\b", combined, re.IGNORECASE):
            if re.search(r"\bbutton\b", combined, re.IGNORECASE):
                return "Arduino Push Button"
            if re.search(r"\bled\b", combined, re.IGNORECASE):
                return "Arduino LED Setup"
            return "Arduino Project"

        if re.search(r"\bsolar\b", combined, re.IGNORECASE):
            return "Solar Energy Overview"
        if re.search(r"\bwelding\b", combined, re.IGNORECASE):
            return "Welding Robot System"
        if re.search(r"\bcnc\b", combined, re.IGNORECASE):
            return "CNC Machine Specs"
        if re.search(r"\b(?:invoice|payment|cost|fee)\b", combined, re.IGNORECASE):
            return "Invoice Payment Details"

        stopwords = {
            "what", "is", "there", "in", "the", "pdf", "a", "an", "can", "you",
            "please", "tell", "me", "about", "this", "and", "or", "to", "of",
            "for", "how", "does", "do", "why", "who", "where", "when", "which",
            "give", "show", "explain", "summarize", "document", "file"
        }

        # Check source filename
        if sources:
            src = sources[0].get("source") or sources[0].get("filename") or ""
            clean_src = re.sub(r"\.(pdf|png|jpe?g|docx?|txt)$", "", src, flags=re.I)
            clean_src = re.sub(r"[_\\-]+", " ", clean_src).strip()
            words = [w.capitalize() for w in clean_src.split() if w.lower() not in stopwords]
            if words:
                return " ".join(words[:3])

        # Extract top keywords from user_msg
        words = [w.capitalize() for w in re.findall(r"\b[a-zA-Z]{3,}\b", user_msg) if w.lower() not in stopwords]
        if words:
            return " ".join(words[:3])

        return "Document Analysis"


