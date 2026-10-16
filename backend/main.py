import os
import sys
import time
import uuid
import json
import logging
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_file, g
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Add both backend and project root directory to path
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
for p in (str(backend_dir), str(project_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from backend.config import UPLOADS_DIR, AUDIO_DIR, ARTIFACTS_DIR, DEFAULT_SETTINGS, DEFAULT_SYSTEM_PROMPT
    from backend.database import get_db, init_db
    from backend.auth import hash_password, verify_password, generate_token, require_auth
    from backend.services.document_service import DocumentService
    from backend.services.vision_service import VisionService
    from backend.services.rag_service import RAGService
    from backend.services.llm_service import LLMService
    from backend.services.agent_service import AgentService, normalize_model_name
    from backend.services.speech_service import SpeechService
    from backend.services.metrics_service import MetricsService
    from backend.services.orchestrator import Orchestrator
except ImportError:
    from config import UPLOADS_DIR, AUDIO_DIR, ARTIFACTS_DIR, DEFAULT_SETTINGS, DEFAULT_SYSTEM_PROMPT
    from database import get_db, init_db
    from auth import hash_password, verify_password, generate_token, require_auth
    from services.document_service import DocumentService
    from services.vision_service import VisionService
    from services.rag_service import RAGService
    from services.llm_service import LLMService
    from services.agent_service import AgentService, normalize_model_name
    from services.speech_service import SpeechService
    from services.metrics_service import MetricsService
    from services.orchestrator import Orchestrator

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("accessai.main")

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize SQLite database
    init_db()

    # -------------------------------------------------------------
    # 1. Authentication Routes
    # -------------------------------------------------------------
    @app.route("/api/auth/register", methods=["POST"])
    def register():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not name or not email or not password:
            return jsonify({"error": "Name, email and password are required"}), 400

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        pwd_hash = hash_password(password)

        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
                    (user_id, name, email, pwd_hash),
                )
                # Seed default settings
                conn.execute(
                    "INSERT INTO settings (user_id, settings_json) VALUES (?, ?)",
                    (user_id, json.dumps(DEFAULT_SETTINGS)),
                )
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                return jsonify({"error": "An account with this email already exists"}), 400
            return jsonify({"error": f"Registration failed: {str(e)}"}), 500

        token = generate_token(user_id, email)
        user = {"id": user_id, "name": name, "email": email}
        return jsonify({"token": token, "user": user}), 201

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        with get_db() as conn:
            row = conn.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
            if not row or not verify_password(password, row["password_hash"]):
                return jsonify({"error": "Invalid email or password"}), 401

            user_id = row["id"]
            user = {"id": user_id, "name": row["name"], "email": row["email"]}

        token = generate_token(user_id, email)
        return jsonify({"token": token, "user": user})

    @app.route("/api/auth/me", methods=["GET", "PUT"])
    @require_auth
    def me():
        user_id = g.user_id
        if request.method == "GET":
            return jsonify(g.current_user)

        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        with get_db() as conn:
            updates = []
            params = []
            if name:
                updates.append("name = ?")
                params.append(name)
            if email:
                updates.append("email = ?")
                params.append(email)
            if password:
                updates.append("password_hash = ?")
                params.append(hash_password(password))

            if updates:
                params.append(user_id)
                conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)

            row = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
            updated_user = dict(row) if row else g.current_user

        return jsonify(updated_user)

    # -------------------------------------------------------------
    # 2. Settings Routes
    # -------------------------------------------------------------
    @app.route("/api/settings", methods=["GET", "PUT"])
    @require_auth
    def settings_endpoint():
        user_id = g.user_id
        with get_db() as conn:
            row = conn.execute("SELECT settings_json FROM settings WHERE user_id = ?", (user_id,)).fetchone()
            current_settings = dict(DEFAULT_SETTINGS)
            if row and row["settings_json"]:
                try:
                    current_settings.update(json.loads(row["settings_json"]))
                except Exception:
                    pass

            if request.method == "GET":
                return jsonify(current_settings)

            patch = request.get_json(silent=True) or {}
            current_settings.update(patch)

            conn.execute(
                "INSERT INTO settings (user_id, settings_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(user_id) DO UPDATE SET settings_json=excluded.settings_json, updated_at=CURRENT_TIMESTAMP",
                (user_id, json.dumps(current_settings)),
            )

        return jsonify(current_settings)

    # -------------------------------------------------------------
    # 3. Conversations Routes
    # -------------------------------------------------------------
    @app.route("/api/conversations", methods=["GET"])
    @require_auth
    def list_conversations():
        user_id = g.user_id
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       COUNT(a.id) AS attachment_count,
                       SUM(CASE WHEN a.kind = 'image' THEN 1 ELSE 0 END) AS image_count,
                       SUM(CASE WHEN a.kind = 'document' THEN 1 ELSE 0 END) AS doc_count
                FROM conversations c
                LEFT JOIN attachments a ON a.conversation_id = c.id
                WHERE c.user_id = ?
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                """,
                (user_id,),
            ).fetchall()
            return jsonify([dict(r) for r in rows])

    @app.route("/api/conversations/<cid>/messages", methods=["GET"])
    @require_auth
    def get_messages(cid):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, role, content, attachments_json, sources_json, artifact_json, latency_ms, model, activities_json, follow_ups_json, created_at "
                "FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (cid,),
            ).fetchall()

            messages = []
            for r in rows:
                m = {
                    "id": r["id"],
                    "role": r["role"],
                    "content": r["content"],
                    "latency_ms": r["latency_ms"],
                    "model": r["model"],
                }
                if r["attachments_json"]:
                    try:
                        m["attachments"] = json.loads(r["attachments_json"])
                    except Exception:
                        pass
                if r["sources_json"]:
                    try:
                        m["sources"] = json.loads(r["sources_json"])
                    except Exception:
                        pass
                if r["artifact_json"]:
                    try:
                        m["artifact"] = json.loads(r["artifact_json"])
                    except Exception:
                        pass
                if "activities_json" in r.keys() and r["activities_json"]:
                    try:
                        m["activities"] = json.loads(r["activities_json"])
                    except Exception:
                        pass
                if "follow_ups_json" in r.keys() and r["follow_ups_json"]:
                    try:
                        m["follow_ups"] = json.loads(r["follow_ups_json"])
                    except Exception:
                        pass
                messages.append(m)

            return jsonify(messages)

    @app.route("/api/conversations/<cid>", methods=["PUT", "DELETE"])
    @require_auth
    def conversation_item(cid):
        user_id = g.user_id
        with get_db() as conn:
            if request.method == "DELETE":
                conn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (cid, user_id))
                return ("", 204)

            data = request.get_json(silent=True) or {}
            title = (data.get("title") or "Untitled").strip()
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                (title, cid, user_id),
            )
            return jsonify({"id": cid, "title": title})

    @app.route("/api/conversations/<cid>/attachments", methods=["GET"])
    @require_auth
    def get_conversation_attachments(cid):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, name, kind, pages, chars, ocr_used, extracted_text, image_description, created_at "
                "FROM attachments WHERE conversation_id = ? ORDER BY created_at ASC",
                (cid,),
            ).fetchall()
            return jsonify([dict(r) for r in rows])

    @app.route("/api/conversations/<cid>/artifacts", methods=["GET"])
    @require_auth
    def get_conversation_artifacts(cid):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, title, kind, file_size, pages, summary_text, created_at "
                "FROM artifacts WHERE conversation_id = ? ORDER BY created_at DESC",
                (cid,),
            ).fetchall()
            arts = []
            for r in rows:
                item = dict(r)
                item["download_url"] = f"/api/artifacts/{r['id']}/download"
                item["view_url"] = f"/api/artifacts/{r['id']}/file"
                arts.append(item)
            return jsonify(arts)

    @app.route("/api/attachments/<att_id>/file", methods=["GET"])
    def get_attachment_file(att_id):
        with get_db() as conn:
            row = conn.execute("SELECT file_path, name FROM attachments WHERE id = ?", (att_id,)).fetchone()
            if not row or not os.path.exists(row["file_path"]):
                return jsonify({"error": "File not found"}), 404
            return send_file(row["file_path"], download_name=row["name"])

    @app.route("/api/artifacts/<art_id>/download", methods=["GET"])
    def download_artifact(art_id):
        with get_db() as conn:
            row = conn.execute("SELECT file_path, title FROM artifacts WHERE id = ?", (art_id,)).fetchone()
            if not row or not os.path.exists(row["file_path"]):
                return jsonify({"error": "Artifact not found"}), 404
            return send_file(row["file_path"], as_attachment=True, download_name=row["title"])

    @app.route("/api/artifacts/<art_id>/file", methods=["GET"])
    def view_artifact(art_id):
        with get_db() as conn:
            row = conn.execute("SELECT file_path, title FROM artifacts WHERE id = ?", (art_id,)).fetchone()
            if not row or not os.path.exists(row["file_path"]):
                return jsonify({"error": "Artifact not found"}), 404
            return send_file(row["file_path"], download_name=row["title"])

    # -------------------------------------------------------------
    # 4. Upload Documents & Images
    # -------------------------------------------------------------
    @app.route("/api/documents", methods=["POST"])
    @require_auth
    def upload_document():
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename"}), 400

        conversation_id = request.form.get("conversation_id")
        orig_name = secure_filename(file.filename) or "document.pdf"
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        save_path = str(UPLOADS_DIR / f"{doc_id}_{orig_name}")
        file.save(save_path)

        # Extract text & run OCR if scanned
        extraction = DocumentService.extract_from_file(save_path, orig_name)
        pages_count = extraction["pages"]
        chars_count = extraction["chars"]
        ocr_used = extraction["ocr_used"]
        pages_data = extraction["pages_data"]

        # Index into FAISS for retrieval
        user_settings = _get_user_settings(g.user_id)
        RAGService.index_document(
            conversation_id=conversation_id,
            filename=orig_name,
            pages_data=pages_data,
            chunk_size=user_settings.get("chunk_size", 800),
            chunk_overlap=user_settings.get("chunk_overlap", 120),
            is_ocr=ocr_used,
        )

        all_text = "\n\n".join([p["text"] for p in pages_data])
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO attachments (id, user_id, conversation_id, name, kind, file_path, pages, chars, ocr_used, extracted_text)
                VALUES (?, ?, ?, ?, 'document', ?, ?, ?, ?, ?)
                """,
                (doc_id, g.user_id, conversation_id, orig_name, save_path, pages_count, chars_count, 1 if ocr_used else 0, all_text),
            )

        return jsonify({
            "id": doc_id,
            "name": orig_name,
            "kind": "document",
            "pages": pages_count,
            "chars": chars_count,
            "ocr_used": ocr_used,
        }), 201

    @app.route("/api/images", methods=["POST"])
    @require_auth
    def upload_image():
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename"}), 400

        conversation_id = request.form.get("conversation_id")
        orig_name = secure_filename(file.filename) or "image.jpg"
        img_id = f"img_{uuid.uuid4().hex[:12]}"
        save_path = str(UPLOADS_DIR / f"{img_id}_{orig_name}")
        file.save(save_path)

        user_settings = _get_user_settings(g.user_id)
        model = user_settings.get("model", "gemma4:31b-cloud")

        # Analyze with OCR and Ollama Multimodal Vision
        analysis = VisionService.analyze_image(save_path, model_id=model)
        ocr_text = analysis["ocr_text"]
        image_desc = analysis["image_description"]

        # Index into FAISS
        RAGService.index_image(
            conversation_id=conversation_id,
            filename=orig_name,
            ocr_text=ocr_text,
            image_description=image_desc,
            file_path=save_path,
        )

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO attachments (id, user_id, conversation_id, name, kind, file_path, pages, chars, ocr_used, extracted_text, image_description)
                VALUES (?, ?, ?, ?, 'image', ?, 1, ?, ?, ?, ?)
                """,
                (img_id, g.user_id, conversation_id, orig_name, save_path, len(ocr_text), 1 if ocr_text else 0, ocr_text, image_desc),
            )

        return jsonify({
            "id": img_id,
            "name": orig_name,
            "kind": "image",
        }), 201

    # -------------------------------------------------------------
    # 5. Media (STT & TTS)
    # -------------------------------------------------------------
    @app.route("/api/stt", methods=["POST"])
    def stt_endpoint():
        if "file" not in request.files:
            return jsonify({"error": "No audio file uploaded"}), 400

        audio_file = request.files["file"]
        language = request.form.get("language", "auto")
        model = request.form.get("model", "base")

        tmp_name = f"stt_{uuid.uuid4().hex[:10]}.webm"
        tmp_path = str(AUDIO_DIR / tmp_name)
        audio_file.save(tmp_path)

        try:
            text = SpeechService.transcribe(tmp_path, model_name=model, language=language)
            return jsonify({"text": text})
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @app.route("/api/tts", methods=["POST"])
    def tts_endpoint():
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        voice = data.get("voice", "af_heart")
        speed = float(data.get("speed", 1.0))

        if not text:
            return jsonify({"error": "Text is required for TTS"}), 400

        wav_bytes = SpeechService.synthesize_speech(text, voice=voice, speed=speed)
        return Response(wav_bytes, mimetype="audio/wav")

    # -------------------------------------------------------------
    # 6. Streaming Chat (SSE) & Scenario Agent Endpoint
    # -------------------------------------------------------------
    @app.route("/api/agent/scenario", methods=["POST"])
    @require_auth
    def agent_scenario_endpoint():
        user_id = g.user_id
        data = request.get_json(silent=True) or {}
        result = Orchestrator.process_request(data, user_id=user_id)
        return jsonify(result)

    @app.route("/api/chat", methods=["POST"])
    @require_auth
    def chat_endpoint():
        user_id = g.user_id
        data = request.get_json(silent=True) or {}
        conversation_id = data.get("conversation_id")
        user_message = (data.get("message") or "").strip()
        attachment_ids = data.get("attachment_ids") or []
        via_voice = bool(data.get("via_voice", False))

        # Direct JSON response if requested
        if request.headers.get("Accept") == "application/json" or data.get("stream") is False:
            result = Orchestrator.process_request(data, user_id=user_id)
            return jsonify(result)

        start_time = time.time()
        user_settings = _get_user_settings(user_id)
        model_name = normalize_model_name(user_settings.get("model", "nemotron-3-ultra:cloud"))
        retrieval_k = int(user_settings.get("retrieval_k", 4))

        # Create or initialize conversation if needed
        is_new_conv = False
        initial_title = None
        if not conversation_id:
            is_new_conv = True
            conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
            # Dynamic 2-to-3 word title generated from the first chat text sent to the LLM
            initial_title = LLMService.generate_chat_title(
                user_message=user_message,
                answer="",
                sources=[],
                settings=user_settings,
            )
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)",
                    (conversation_id, user_id, initial_title),
                )
        else:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT id, title, (SELECT COUNT(*) FROM messages WHERE conversation_id = ?) as msg_cnt FROM conversations WHERE id = ?",
                    (conversation_id, conversation_id),
                ).fetchone()
                if not row:
                    is_new_conv = True
                    initial_title = LLMService.generate_chat_title(
                        user_message=user_message,
                        answer="",
                        sources=[],
                        settings=user_settings,
                    )
                    conn.execute(
                        "INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)",
                        (conversation_id, user_id, initial_title),
                    )
                elif row["msg_cnt"] == 0 or row["title"] in ("Accessibility Session", "New conversation", "Untitled", None):
                    is_new_conv = True
                    initial_title = LLMService.generate_chat_title(
                        user_message=user_message,
                        answer="",
                        sources=[],
                        settings=user_settings,
                    )
                    conn.execute(
                        "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (initial_title, conversation_id),
                    )
                else:
                    conn.execute(
                        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (conversation_id,),
                    )

        # Retrieve relevant passages from FAISS
        sources = []
        if user_message:
            sources = RAGService.retrieve(conversation_id, user_message, top_k=retrieval_k)

        # If specific attachment IDs passed in the current turn, link to conversation and include in evidence
        turn_attachments = []
        if attachment_ids:
            with get_db() as conn:
                for att_id in attachment_ids:
                    row = conn.execute(
                        "SELECT id, name, kind, file_path, extracted_text, image_description FROM attachments WHERE id = ?",
                        (att_id,),
                    ).fetchone()
                    if row:
                        turn_attachments.append({
                            "id": row["id"],
                            "name": row["name"],
                            "kind": row["kind"],
                        })
                        conn.execute("UPDATE attachments SET conversation_id = ? WHERE id = ?", (conversation_id, att_id))
                        if row["kind"] == "image":
                            if row["image_description"]:
                                sources.append({
                                    "type": "image",
                                    "source": row["name"],
                                    "filename": row["name"],
                                    "file_id": row["id"],
                                    "file_path": row["file_path"],
                                    "page": 1,
                                    "score": 0.98,
                                    "text": f"Visual scene: {row['image_description']}",
                                    "image_description": row["image_description"],
                                    "ocr_text": row["extracted_text"],
                                })
                            if row["extracted_text"]:
                                sources.append({
                                    "type": "ocr",
                                    "source": row["name"],
                                    "filename": row["name"],
                                    "file_id": row["id"],
                                    "file_path": row["file_path"],
                                    "page": 1,
                                    "score": 0.95,
                                    "text": f"Extracted text: {row['extracted_text']}",
                                })
                        else:
                            if row["extracted_text"]:
                                sources.append({
                                    "type": "document",
                                    "source": row["name"],
                                    "filename": row["name"],
                                    "file_id": row["id"],
                                    "file_path": row["file_path"],
                                    "page": 1,
                                    "score": 0.96,
                                    "text": row["extracted_text"][:1200],
                                })

        # Also ensure any conversation image attachments are in sources with file_path for multimodal models
        with get_db() as conn:
            existing_attachments = conn.execute(
                "SELECT id, name, kind, file_path, extracted_text, image_description FROM attachments WHERE conversation_id = ? ORDER BY created_at DESC",
                (conversation_id,),
            ).fetchall()
            for r in existing_attachments:
                if r["kind"] == "image":
                    if not any(s.get("source") == r["name"] and s.get("type") == "image" for s in sources):
                        sources.append({
                            "type": "image",
                            "source": r["name"],
                            "filename": r["name"],
                            "file_id": r["id"],
                            "file_path": r["file_path"],
                            "page": 1,
                            "score": 0.98,
                            "text": f"Visual scene: {r['image_description']}" if r["image_description"] else f"Image {r['name']} in conversation.",
                            "image_description": r["image_description"],
                            "ocr_text": r["extracted_text"],
                        })
                    if r["extracted_text"] and not any(s.get("source") == r["name"] and s.get("type") == "ocr" for s in sources):
                        sources.append({
                            "type": "ocr",
                            "source": r["name"],
                            "filename": r["name"],
                            "file_id": r["id"],
                            "file_path": r["file_path"],
                            "page": 1,
                            "score": 0.95,
                            "text": f"Extracted text: {r['extracted_text']}",
                        })

        # Fetch conversation history from database
        history_messages = []
        with get_db() as conn:
            prior_rows = conn.execute(
                "SELECT role, content FROM (SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 12) ORDER BY created_at ASC",
                (conversation_id,),
            ).fetchall()
            for r in prior_rows:
                history_messages.append({"role": r["role"], "content": r["content"]})

        if user_message:
            history_messages.append({"role": "user", "content": user_message})

        # Save user message to database with attachments
        user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        with get_db() as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, attachments_json) VALUES (?, ?, 'user', ?, ?)",
                (user_msg_id, conversation_id, user_message, json.dumps(turn_attachments) if turn_attachments else None),
            )

        def event_stream():
            full_reply = ""
            created_artifact = None
            final_activities = []
            final_summary = ""
            follow_ups = []
            try:
                # 1. Emit meta and title event immediately
                with get_db() as conn:
                    crow = conn.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
                    conv_title = crow["title"] if crow else ""
                yield f"event: meta\ndata: {json.dumps({'conversation_id': conversation_id, 'title': conv_title})}\n\n"
                if conv_title:
                    yield f"event: title\ndata: {json.dumps({'conversation_id': conversation_id, 'title': conv_title})}\n\n"

                # 2. Emit initial sources event
                if sources:
                    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

                # 3. Stream events from AgentService
                for event_type, data in AgentService.run_agent(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    user_message=user_message,
                    attachment_ids=attachment_ids or [],
                    history_messages=history_messages,
                    settings=user_settings,
                ):
                    if event_type in ("token", "answer_delta"):
                        tok = data.get("text") or data.get("delta", "")
                        full_reply += tok
                        yield f"event: token\ndata: {json.dumps({'text': tok})}\n\n"
                        yield f"event: answer_delta\ndata: {json.dumps({'delta': tok, 'text': tok})}\n\n"
                    elif event_type == "follow_ups":
                        follow_ups = data.get("suggestions", [])
                        yield f"event: follow_ups\ndata: {json.dumps(data)}\n\n"
                    elif event_type == "artifact":
                        created_artifact = data
                        yield f"event: artifact\ndata: {json.dumps(data)}\n\n"
                    elif event_type in ("sources", "sources_available"):
                        if isinstance(data, list):
                            for s_item in data:
                                if not any(x.get("source") == s_item.get("source") and x.get("type") == s_item.get("type") for x in sources):
                                    sources.insert(0, s_item)
                        yield f"event: {event_type}\ndata: {json.dumps(sources if isinstance(data, list) else data)}\n\n"
                    elif event_type == "task_completed":
                        final_activities = data.get("activities", [])
                        final_summary = data.get("activity_summary", "")
                        yield f"event: task_completed\ndata: {json.dumps(data)}\n\n"
                    elif event_type in ("error", "task_error"):
                        yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                    else:
                        # tool_started, tool_completed, tool_failed, activity, task_started, status_update
                        if event_type == "activity" and isinstance(data, dict):
                            final_activities.append(data)
                        elif event_type in ("tool_started", "tool_completed", "tool_failed") and isinstance(data, dict) and data.get("id"):
                            # These are flat activity dicts from the new orchestrator
                            existing = next((a for a in final_activities if a.get("id") == data["id"]), None)
                            if existing:
                                existing.update(data)
                            else:
                                final_activities.append(data)
                        yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

                latency_ms = int((time.time() - start_time) * 1000)

                # 4. Save assistant reply to database
                asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
                with get_db() as conn:
                    conn.execute(
                        """
                        INSERT INTO messages (id, conversation_id, role, content, sources_json, artifact_json, latency_ms, model, activities_json, follow_ups_json)
                        VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            asst_msg_id,
                            conversation_id,
                            full_reply,
                            json.dumps(sources),
                            json.dumps(created_artifact) if created_artifact else None,
                            latency_ms,
                            model_name,
                            json.dumps(final_activities) if final_activities else None,
                            json.dumps(follow_ups) if follow_ups else None,
                        ),
                    )

                # 5. Dynamic 2-to-3 word chat title generated by AI
                try:
                    with get_db() as conn:
                        row = conn.execute(
                            "SELECT title, (SELECT COUNT(*) FROM messages WHERE conversation_id = ?) as msg_count FROM conversations WHERE id = ?",
                            (conversation_id, conversation_id),
                        ).fetchone()
                        curr_title = row["title"] if row else ""
                        msg_count = row["msg_count"] if row else 0

                    is_generic = (
                        is_new_conv
                        or msg_count <= 2
                        or not curr_title
                        or curr_title in ("Accessibility Session", "New conversation", "Untitled", "Document Analysis")
                        or len(curr_title.split()) > 4
                    )
                    if is_generic and full_reply:
                        dynamic_title = LLMService.generate_chat_title(
                            user_message=user_message,
                            answer=full_reply,
                            sources=sources,
                            settings=user_settings,
                        )
                        if dynamic_title:
                            with get_db() as conn:
                                conn.execute(
                                    "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                    (dynamic_title, conversation_id),
                                )
                            yield f"event: title\ndata: {json.dumps({'conversation_id': conversation_id, 'title': dynamic_title})}\n\n"
                except Exception as t_err:
                    logger.warning("Dynamic chat title generation skipped: %s", t_err)

                # 6. Emit done event
                yield f"event: done\ndata: {json.dumps({'latency_ms': latency_ms, 'model': model_name})}\n\n"

            except Exception as e:
                logger.error("SSE stream error: %s", e)
                yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

        return Response(event_stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # -------------------------------------------------------------
    # 7. Metrics & Evaluation
    # -------------------------------------------------------------
    @app.route("/api/metrics", methods=["GET"])
    def metrics_dashboard():
        metrics = MetricsService.get_metrics_dashboard()
        return jsonify(metrics)

    @app.route("/api/metrics/run", methods=["POST"])
    def run_metrics():
        data = request.get_json(silent=True) or {}
        suite = data.get("suite", "all")
        result = MetricsService.run_suite(suite=suite)
        return jsonify(result)

    def _get_user_settings(user_id: str) -> dict:
        with get_db() as conn:
            row = conn.execute("SELECT settings_json FROM settings WHERE user_id = ?", (user_id,)).fetchone()
            cfg = dict(DEFAULT_SETTINGS)
            if row and row["settings_json"]:
                try:
                    cfg.update(json.loads(row["settings_json"]))
                except Exception:
                    pass
            if "model" in cfg:
                cfg["model"] = normalize_model_name(cfg["model"])
            return cfg

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting AccessAI backend server on http://localhost:{port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
