/**
 * Wire types mirroring backend/app/models/*.py.
 * Keep these in lock-step with API.md.
 */

export type RecordingStatus =
  | "pending"
  | "downloading"
  | "transcribing"
  | "analyzing"
  | "saving"
  | "completed"
  | "failed";

export interface RecordingListItem {
  id: string;
  status: RecordingStatus;
  title: string | null;
  conversationType: string | null;
  sentiment: string | null;
  createdAt: string; // ISO 8601 UTC with `Z`
}

export interface RecordingListResponse {
  items: RecordingListItem[];
  total: number;
}

export interface TranscriptSegment {
  speaker: string | null;
  role: string | null;
  start: number | null;
  end: number | null;
  text: string;
}

export interface Transcript {
  language: string | null;
  text: string;
  segments: TranscriptSegment[];
}

export interface ActionItem {
  action: string;
  department: string | null;
  priority: "low" | "medium" | "high";
  status: "requested" | "promised" | "completed" | "unknown";
}

export interface ImportantDetail {
  key: string;
  value: string;
}

export interface Sentiment {
  label: "positive" | "neutral" | "negative";
  score: number;
}

export interface Analysis {
  title: string;
  summary: string;
  conversationType:
    | "booking"
    | "complaint"
    | "inquiry"
    | "cancellation"
    | "check_in"
    | "check_out"
    | "maintenance"
    | "request"
    | "general"
    | "other";
  sentiment: Sentiment;
  keyPoints: string[];
  complaints: string[];
  requests: string[];
  actionItems: ActionItem[];
  importantDetails: ImportantDetail[];
  followUpRequired: boolean;
}

export interface RecordingError {
  code: string;
  message: string;
}

export interface RecordingDetail {
  id: string;
  status: RecordingStatus;
  createdAt?: string | null;
  completedAt?: string | null;
  transcript?: Transcript | null;
  analysis?: Analysis | null;
  error?: RecordingError | null;
}

export interface CreateRecordingResponse {
  id: string;
  status: RecordingStatus;
}

export interface ApiErrorBody {
  error: { code: string; message: string };
}
