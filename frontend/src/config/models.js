export const MODELS = [
  { id: 'nemotron-3-ultra:cloud', label: 'Nemotron 3 Ultra', family: 'NVIDIA', size: '550B' },
  { id: 'gemma4:31b-cloud', label: 'Gemma 4 31B', family: 'Google', size: '31B', multimodal: true },
  { id: 'gpt-oss:20b-cloud', label: 'GPT-OSS 20B', family: 'OpenAI', size: '20B' },
  { id: 'gpt-oss:120b-cloud', label: 'GPT-OSS 120B', family: 'OpenAI', size: '120B' },
];

export const modelLabel = (id) => MODELS.find((m) => m.id === id)?.label ?? id;

export const DEFAULT_SYSTEM_PROMPT = `You are AccessAI — an intelligent, context-aware, multimodal accessibility agent.
You assist both visually impaired and sighted users with documents (PDFs, reports), images (photos, charts, scene understanding, OCR), and natural conversation.

Key capabilities & instructions:
1. Natural & Conversational: Talk warmly, naturally, and engagingly like ChatGPT. Answer greetings, normal chit-chat, explanations, follow-ups, and user requests smoothly without robotic refusals.
2. Context & Media Aware: You have direct access to the user's uploaded library of documents and images, short-term conversation context, and long-term user memories. When asked about user images or documents (e.g. "what images did I give you?", "describe my pictures", "what PDFs do I have?"), give complete, accurate, organized answers citing their names and contents.
3. Multimodal Analysis:
   - For images: Describe scenes, objects, text, colors, and visual layout clearly.
   - For PDFs/Documents: Explain specific topics thoroughly based on the verified contents and extracted pages.
   - For summaries & reports: When asked to summarize a document or create a summary PDF, provide a clear structured overview and explain that a downloadable report is prepared for them.
4. Voice & Speech-Friendly: Keep explanations structured and articulate so they can be read aloud cleanly by Text-to-Speech (TTS).`;

export const DEFAULT_SETTINGS = {
  model: 'nemotron-3-ultra:cloud',
  temperature: 0.3,
  top_p: 0.9,
  top_k: 40,
  num_ctx: 8192,
  num_predict: 1024,
  repeat_penalty: 1.1,
  seed: null,
  system_prompt: DEFAULT_SYSTEM_PROMPT,
  retrieval_k: 4,
  chunk_size: 800,
  chunk_overlap: 120,
  grounded_only: true,
  stt_model: 'base',
  stt_language: 'auto',
  tts_voice: 'af_heart',
  tts_speed: 1,
  auto_speak: 'voice',
  auto_send: true,
};

export const PARAMS = [
  { key: 'temperature', label: 'Temperature', min: 0, max: 2, step: 0.05, hint: 'Lower is more factual. Higher is more creative.' },
  { key: 'top_p', label: 'Top-p', min: 0.1, max: 1, step: 0.05, hint: 'Nucleus sampling cut-off.' },
  { key: 'top_k', label: 'Top-k', min: 1, max: 200, step: 1, hint: 'Number of candidate tokens considered.' },
  { key: 'num_ctx', label: 'Context length', min: 2048, max: 131072, step: 1024, hint: 'Tokens the model can read at once.' },
  { key: 'num_predict', label: 'Max output tokens', min: 64, max: 8192, step: 64, hint: 'Upper limit for one answer.' },
  { key: 'repeat_penalty', label: 'Repeat penalty', min: 1, max: 2, step: 0.05, hint: 'Discourages repeated phrases.' },
];

export const RETRIEVAL_PARAMS = [
  { key: 'retrieval_k', label: 'Passages retrieved', min: 1, max: 12, step: 1, hint: 'Top-k chunks sent to the model.' },
  { key: 'chunk_size', label: 'Chunk size', min: 200, max: 2000, step: 50, hint: 'Characters per text chunk.' },
  { key: 'chunk_overlap', label: 'Chunk overlap', min: 0, max: 500, step: 10, hint: 'Characters shared between chunks.' },
];

export const STT_MODELS = ['tiny', 'base', 'small'];
export const STT_LANGUAGES = [
  ['auto', 'Auto-detect'], ['en', 'English'], ['hi', 'Hindi'], ['ta', 'Tamil'], ['te', 'Telugu'],
  ['kn', 'Kannada'], ['ml', 'Malayalam'], ['es', 'Spanish'], ['fr', 'French'], ['de', 'German'],
];
export const TTS_VOICES = [
  ['af_heart', 'Heart (US, female)'], ['af_bella', 'Bella (US, female)'], ['am_michael', 'Michael (US, male)'],
  ['bf_emma', 'Emma (UK, female)'], ['bm_george', 'George (UK, male)'],
];
export const AGENT_SUGGESTIONS = [
  {
    icon: 'FileText',
    title: 'Summarize Document',
    prompt: 'Summarize this document',
    description: 'Get key takeaways, structure, and highlights from any file.',
  },
  {
    icon: 'Search',
    title: 'Analyze Key Topics',
    prompt: 'What are the main topics covered?',
    description: 'Break down main sections, outline, and technical findings.',
  },
  {
    icon: 'Image',
    title: 'Inspect Photo or Image',
    prompt: 'Describe this image and its text',
    description: 'Understand visual scenes, diagrams, objects, and OCR text.',
  },
  {
    icon: 'FileSpreadsheet',
    title: 'Generate PDF Report',
    prompt: 'Generate a summary PDF report',
    description: 'Produce a downloadable executive PDF report.',
  },
];

export const SUGGESTIONS = AGENT_SUGGESTIONS.map((s) => s.prompt);

