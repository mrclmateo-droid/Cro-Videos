export const PROCESSING = ["transcribing", "analyzing", "finding_highlights"];

export const PROJECT_STATUS: Record<string, { label: string; tone: "gray" | "blue" | "green" | "red" | "violet"; busy?: boolean }> = {
  created: { label: "Nuevo", tone: "gray" },
  uploading: { label: "Subiendo", tone: "blue", busy: true },
  transcribing: { label: "Transcribiendo", tone: "violet", busy: true },
  analyzing: { label: "Analizando", tone: "violet", busy: true },
  finding_highlights: { label: "Buscando momentos", tone: "violet", busy: true },
  ready: { label: "Listo", tone: "green" },
  error: { label: "Error", tone: "red" },
};

export const CATEGORIES: Record<string, string> = {
  educational: "Educativo",
  entertainment: "Entretenimiento",
  storytelling: "Storytelling",
  opinion: "Opinión",
  emotional: "Emocional",
};

export const SCORE_LABELS: Record<string, string> = {
  hook: "Gancho", clarity: "Claridad", relevance: "Relevancia", emotion: "Emoción",
  informational_value: "Valor informativo", standalone: "Autonomía", pacing: "Ritmo",
  retention: "Retención", closing: "Cierre",
};
