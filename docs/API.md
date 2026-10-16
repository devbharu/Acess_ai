# AccessAI API contract (frontend -> Flask)

All routes under `/api`. JSON unless noted. Auth: `Authorization: Bearer <token>`; 401 clears the session.
Errors: `{"error": "message"}` with a non-2xx status.

| Method | Route | Body | Returns |
|---|---|---|---|
| POST | /auth/register | name, email, password | {token, user} |
| POST | /auth/login | email, password | {token, user} |
| GET / PUT | /auth/me | PUT: name?, email?, password? | user {id,name,email} |
| GET / PUT | /settings | PUT: partial settings | settings object |
| GET | /conversations | | [{id,title}] |
| GET | /conversations/:id/messages | | [{id,role,content,attachments?,sources?,latency_ms?,model?}] |
| PUT / DELETE | /conversations/:id | title | |
| POST | /documents | multipart: file, conversation_id? | {id, name, kind:"document", pages, chars, ocr_used} |
| POST | /images | multipart: file, conversation_id? | {id, name, kind:"image"} |
| POST | /stt | multipart: file, language?, model? | {text} |
| POST | /tts | {text, voice, speed} | audio/wav |
| POST | /chat | {conversation_id|null, message, attachment_ids[], via_voice} | SSE stream |
| GET | /metrics | | {summary, history, robustness, latency, runs} |
| POST | /metrics/run | {suite: all\|stt\|ocr\|qa} | new run |

SSE events from `/chat`: `meta {conversation_id}`, `token {text}`, `sources [{type,source,page,score,text}]`,
`done {latency_ms, model}`, `error {message}`.

Settings keys: model, temperature, top_p, top_k, num_ctx, num_predict, repeat_penalty, seed, system_prompt,
retrieval_k, chunk_size, chunk_overlap, grounded_only, stt_model, stt_language, tts_voice, tts_speed, auto_speak, auto_send.
