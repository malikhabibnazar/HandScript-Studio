export type Sample = {
  id: string;
  filename: string;
  added: string;
  quality: number;
  characters: number;
};

export type Analysis = {
  character_coverage: number;
  sample_quality: number;
  samples_analyzed: number;
  avg_stroke_width: number;
  slant_degrees: number;
  baseline_stability: number;
  spacing_consistency: number;
  notes: string[];
};

export type HandwritingEngineName = "graves" | "handwrite" | "pillow" | "hw2font" | "fontmaker" | "gemini" | "onedm";

export type PillowFace = "caveat" | "homemade" | "patrick" | "kalam" | "sacramento" | "architects";

export type ProfileStyle = {
  style_id: number;
  bias: number;
  variation: number;
  engine: HandwritingEngineName;
  font_family: PillowFace;
  font_path?: string | null;
};

export type FaceInfo = {
  id: PillowFace;
  label: string;
  installed: boolean;
};

export type SheetStatus = {
  potrace: boolean;
  fontforge: boolean;
  hw2font: boolean;
  fontmaker: boolean;
  personal_font: boolean;
};

export type HandwriteStatus = {
  package: boolean;
  version: string | null;
  potrace: boolean;
  fontforge: boolean;
  personal_font: boolean;
  bundled_font: boolean;
};

export type OneDMStatus = {
  installed: boolean;
  weights_path: string;
  weights_loaded: boolean;
  device: string;
  device_label: string;
  directml_available: boolean;
  cuda_available: boolean;
  rx_580_compatible: boolean;
  message: string;
};

export type HandwritingStatus = {
  requested: string;
  active: string;
  weights_loaded: boolean;
  message: string;
  default_style_id: number;
  style_ids: number[];
  handwrite?: HandwriteStatus;
  faces?: FaceInfo[];
  sheets?: SheetStatus;
  gemini?: { configured: boolean; model: string };
  onedm?: OneDMStatus;
};

export type Profile = {
  id: string;
  name: string;
  description: string;
  status: string;
  samples: Sample[];
  created: string;
  is_default: boolean;
  analysis: Analysis | null;
  style: ProfileStyle | null;
  preview_text: string;
  sample_count: number;
};

export type Element = {
  id: string;
  type: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  align: string;
  font_size: number;
  content: string;
  visible: boolean;
};

export type Template = {
  id: string;
  name: string;
  kind: string;
  width_in: number;
  height_in: number;
  status: string;
  modified: string;
  elements: Element[];
  margin_in: number;
  description: string;
};

export type DocumentItem = {
  id: string;
  name: string;
  template_id: string;
  template_name: string;
  profile_id: string;
  profile_name: string;
  status: string;
  export_format: string;
  created: string;
  modified: string;
  pages: number;
  fields: Record<string, string>;
};

export type DocumentDetail = DocumentItem & {
  template: Template | null;
  profile: Profile | null;
};

export type ImportIssue = {
  line: number;
  reason: string;
};

export type ImportSummary = {
  id: string;
  filename: string;
  records_detected: number;
  valid_records: number;
  invalid_records: number;
  columns: string[];
  rows: Record<string, string>[];
  issues: ImportIssue[];
};

export type Batch = {
  id: string;
  name: string;
  template_id: string;
  template_name: string;
  profile_id: string;
  profile_name: string;
  status: string;
  total: number;
  generated: number;
  failed: number;
  created: string;
  export_format: string;
  output_dir: string;
  current_item: string;
  naming: string;
  individual: boolean;
  combined: boolean;
  runnable: boolean;
  error: string;
  progress: number;
};

export type ExportRecord = {
  id: string;
  batch_id: string;
  batch_name: string;
  date: string;
  file_count: number;
  format: string;
  status: string;
  output_dir: string;
  size_mb: number;
  has_file: boolean;
};

export type Activity = {
  id: string;
  kind: string;
  title: string;
  detail: string;
  when: string;
};

export type Dashboard = {
  counts: {
    profiles: number;
    templates: number;
    documents_generated: number;
    recent_batches: number;
  };
  activity: Activity[];
  system: Record<string, string>;
};

export type Settings = {
  workspace: string;
  output_dir: string;
  default_template_id: string;
  default_profile_id: string;
  theme: string;
  ui_scale: number;
  reduce_motion: boolean;
  export_format: string;
  resolution: string;
  pause_on_error: boolean;
  notify_on_complete: boolean;
  printer: string;
  page_scaling: string;
  print_margins: string;
  onboarding_complete: boolean;
  cache_bytes: number;
};
