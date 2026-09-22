export type Project = {
  id: string; name: string; status: string; error: string | null; created_at: string; updated_at: string;
};
export type Video = {
  id: string; project_id: string; filename: string; size: number | null; duration: number | null;
  width: number | null; height: number | null; fps: number | null; upload_status: string; created_at: string;
};
export type ProjectStatus = { project: Project; video: Video | null; highlights_count: number };

export type Word = { w: string; s: number; e: number };
export type Segment = { idx: number; start: number; end: number; text: string; speaker_id: string | null; words: Word[] };
export type Transcript = { video_id: string; language: string | null; status: string; segments: Segment[] };

export type Highlight = {
  id: string; video_id: string; start: number; end: number; duration: number; title: string; reason: string;
  category: string | null; scores: Record<string, number>; overall: number;
};

export type Clip = {
  id: string; project_id: string; video_id: string; highlight_id: string | null; start: number; end: number;
  duration: number; preset: string; status: string; created_at: string;
};

export type CaptionStyle = {
  font: string; font_size_pct: number; primary_color: string; highlight_color: string; outline_color: string;
  outline_width: number; shadow: number; bold: boolean; uppercase: boolean; max_words: number;
  highlight_active_word: boolean;
};
export type Caption = { id: string; clip_id: string; style: CaptionStyle; words: Word[] };
export type Preset = { id: string; label: string; caption_style: CaptionStyle };

export type Aspect = "9:16" | "1:1" | "16:9";
export type Resolution = "720p" | "1080p";
export type Render = {
  id: string; clip_id: string; aspect: string; resolution: string; status: string; progress: number;
  error: string | null; attempts: number; export_id: string | null;
};

export type UploadStartOut = { video_id: string; part_size: number; parts: { part_number: number; url: string }[] };
