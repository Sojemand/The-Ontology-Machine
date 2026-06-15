import type { KernelPendingInteractionState } from "./types.ts";

export interface KernelDialogCallbacks {
  onSubmit: (payload: Record<string, unknown>, actionLabel: string) => void;
  onCancel: (payload: { response_status: "cancelled" | "closed" | "expired"; cancellation_reason: string }, actionLabel: string) => void;
}

export interface KernelDialogDraftState {
  pathValue?: string;
  textValue?: string;
  selectedDatabasePaths?: string[];
}

export interface TextInputOptions {
  helperText?: string;
  multiline?: boolean;
}

export type DraftStateUpdater = (requestId: string, patch: Partial<KernelDialogDraftState>) => void;

export type PendingKernelInteraction = KernelPendingInteractionState | null;
